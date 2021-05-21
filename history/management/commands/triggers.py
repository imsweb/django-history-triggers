import hashlib

from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.utils.encoding import force_bytes

from history import conf


def truncate_long_name(name):
    # This is copied from django to shorten names that would exceed postgres's limit of
    # 63 characters. Originally found in django/db/backends/utils.py in "truncate_name"
    # Django source code:
    # https://github.com/django/django/blob/stable/1.5.x/django/db/backends/util.py#L133
    hsh = hashlib.md5(force_bytes(name)).hexdigest()[:5]
    return "%s_%s" % (name[:57], hsh) if len(name) > 63 else name


def maybe_quote(value):
    """
    Used for quoting the HISTORY_DEFAULT_USER value, if it's a string.
    """
    if value is None:
        return "NULL"
    elif isinstance(value, str):
        return "'%s'" % value.replace("'", "''")
    return value


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--drop",
            action="store_true",
            dest="drop",
            default=False,
            help="Drop triggers instead of creating them",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            dest="clear",
            default=False,
            help="Drop the history schema in addition to triggers",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        cursor = connections["default"].cursor()
        dropping = options.get("drop", False)
        if not dropping:
            create_history_schema(cursor)
        table_names = get_base_tables(cursor)
        action_verb = "Dropping" if dropping else "Creating"
        for table_name in sorted(table_names):
            pk_name, pk_type = table_names[table_name]
            if not dropping and create_history_table(
                cursor, table_name, pk_name, pk_type
            ):
                print("Created history table for %s (pk=%s)" % (table_name, pk_name))
            print("%s triggers for %s" % (action_verb, table_name))
            for trigger_type in ("insert", "update", "delete"):
                if dropping:
                    drop_trigger(cursor, trigger_type, table_name)
                else:
                    create_trigger(cursor, trigger_type, table_name, pk_name)
        print("%s triggers is complete. No errors were raised." % action_verb)
        if options["clear"]:
            print('Dropping schema "%s"' % conf.SCHEMA_NAME)
            cursor.execute("DROP SCHEMA IF EXISTS %s CASCADE" % conf.SCHEMA_NAME)


def schema_exists(cursor, schema_name):
    """
    Returns whether or not a schema exists in the DB given the schema name.
    """
    cursor.execute(
        """
        SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = %s)
        """,
        (schema_name,),
    )
    return cursor.fetchone()[0]


def table_exists(cursor, table_name, schema_name="public"):
    """
    Returns whether or not a table exists in the DB given the table and schema name
    (default 'public').
    """
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = %s AND table_schema = %s
        )
        """,
        (table_name, schema_name),
    )
    return cursor.fetchone()[0]


def trigger_exists(cursor, trigger_name, schema_name="public"):
    """
    Returns whether or not the trigger function exists in the DB.
    """
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.triggers
            WHERE trigger_schema = %s AND trigger_name = %s
        )
        """,
        (schema_name, trigger_name),
    )
    return cursor.fetchone()[0]


def get_base_tables(cursor, schema_name="public"):
    """
    Returns all of the tables in the public schema which are not lkups and not in the
    exclude list.
    """
    cursor.execute(
        """
        SELECT
            t.table_name,
            COALESCE(kcu.column_name, ''),
            c.data_type,
            c.character_maximum_length
        FROM information_schema.tables t
        LEFT OUTER JOIN information_schema.table_constraints tc ON
            tc.table_schema = t.table_schema AND tc.table_name = t.table_name
                AND tc.constraint_type = 'PRIMARY KEY'
        LEFT OUTER JOIN information_schema.key_column_usage kcu ON
            kcu.table_schema = tc.table_schema AND kcu.table_name = tc.table_name
                AND kcu.constraint_name = tc.constraint_name
        LEFT OUTER JOIN information_schema.columns c ON
            c.table_schema = kcu.table_schema AND c.table_name = kcu.table_name
                AND c.column_name = kcu.column_name
        WHERE t.table_schema = %s AND t.table_type != 'VIEW'
        """,
        (schema_name,),
    )
    table_names = {}
    for row in cursor.fetchall():
        name = row[0].strip().lower()
        valid = True
        if name in conf.IGNORED_TABLES:
            valid = False
        for prefix in conf.IGNORED_PREFIXES:
            if name.startswith(prefix):
                valid = False
        # Ignore tables without a PRIMARY KEY defined.
        if not row[1].strip():
            valid = False
        if valid:
            pk_type = row[2]
            # Add maximum length if pk_type is character varying.
            if row[3]:
                pk_type += "(%s)" % (row[3])
            table_names[row[0]] = (row[1], pk_type)
    return table_names


def get_table_columns(cursor, table_name, schema_name="public"):
    """
    Returns a list of columns for the given table but excludes text and binary columns
    as well as any column named date_modified or date_last_modified since we don't track
    history for those.
    """
    params = {
        "schema": schema_name,
        "table": table_name,
    }
    cursor.execute(
        """
        SELECT
            column_name,
            CASE WHEN data_type = 'USER-DEFINED' THEN udt_name ELSE data_type END
        FROM information_schema.columns
        WHERE table_schema = '%(schema)s' AND table_name = '%(table)s'
        ORDER BY column_name
        """
        % params
    )
    for row in cursor.fetchall():
        if row[1].lower() in conf.IGNORED_TYPES:
            continue
        if row[0].lower() in conf.IGNORED_COLUMNS:
            continue
        if "%s.%s" % (table_name, row[0].lower()) in conf.IGNORED_COLUMNS:
            continue
        yield row[0], row[1]


def create_history_schema(cursor):
    """
    Create the history schema if it doesn't already exist.
    """
    if not schema_exists(cursor, conf.SCHEMA_NAME):
        params = {
            "name": conf.SCHEMA_NAME,
            "role": conf.DB_ROLE,
        }
        cursor.execute(
            """
            CREATE SCHEMA %(name)s AUTHORIZATION %(role)s;
            GRANT ALL ON SCHEMA %(name)s TO %(role)s;
            REVOKE ALL ON SCHEMA %(name)s FROM public;
            """
            % params
        )


def create_history_table(cursor, base_table, pk_name, pk_type):
    """
    Builds the history table (if it doesn't already exist) given the base table name.
    """
    history_table = truncate_long_name(base_table + "_history").lower()
    if not table_exists(cursor, history_table, conf.SCHEMA_NAME):
        params = {
            "schema": conf.SCHEMA_NAME,
            "table": history_table,
            "role": conf.DB_ROLE,
            "timestamp_type": "timestamp with time zone"
            if conf.USE_TIMEZONES
            else "timestamp",
            "pk_name": pk_name,
            "pk_type": pk_type,
            "user_field": conf.USER_FIELD,
            "user_type": conf.USER_TYPE,
            "field_column": "" if conf.USE_JSON else "field_name varchar(64) not null,",
            "value_type": "jsonb" if conf.USE_JSON else "text",
        }
        cursor.execute(
            """
            CREATE TABLE %(schema)s.%(table)s (
                %(pk_name)s %(pk_type)s not null,
                %(field_column)s
                old_value %(value_type)s,
                new_value %(value_type)s,
                date_modified %(timestamp_type)s not null,
                %(user_field)s %(user_type)s,
                transaction_type char(1) not null
            );
            ALTER TABLE %(schema)s.%(table)s OWNER TO %(role)s;
            REVOKE ALL ON TABLE %(schema)s.%(table)s FROM %(role)s;
            GRANT INSERT, SELECT ON TABLE %(schema)s.%(table)s TO %(role)s;
            """
            % params
        )
        return True
    return False


def get_field_history_sql(trigger_type, table_name, field_name, field_type, pk_name):
    history_table_name = truncate_long_name(table_name + "_history")
    params = {
        "field": field_name,
        "history_table": "%s.%s" % (conf.SCHEMA_NAME, history_table_name),
        "pk_name": pk_name,
        "user_field": conf.USER_FIELD,
    }
    if trigger_type == "insert":
        return (
            """
            -- %(field)s
            INSERT INTO %(history_table)s (
                %(pk_name)s,
                field_name,
                old_value,
                new_value,
                date_modified,
                %(user_field)s,
                transaction_type
            )
            VALUES (
                NEW.%(pk_name)s,
                '%(field)s',
                NULL,
                NEW."%(field)s",
                _dlm,
                _user_id,
                '+'
            );
            """
            % params
        )
    elif trigger_type == "delete":
        return (
            """
            -- %(field)s
            INSERT INTO %(history_table)s (
                %(pk_name)s,
                field_name,
                old_value,
                new_value,
                date_modified,
                %(user_field)s,
                transaction_type
            )
            VALUES (
                OLD.%(pk_name)s,
                '%(field)s',
                OLD."%(field)s",
                NULL,
                _dlm,
                _user_id,
                '-'
            );
            """
            % params
        )
    elif trigger_type == "update":
        return (
            """
            -- %(field)s
            IF (OLD."%(field)s" IS DISTINCT FROM NEW."%(field)s") THEN
                INSERT INTO %(history_table)s (
                    %(pk_name)s,
                    field_name,
                    old_value,
                    new_value,
                    date_modified,
                    %(user_field)s,
                    transaction_type
                )
                VALUES (
                    OLD.%(pk_name)s,
                    '%(field)s',
                    OLD."%(field)s",
                    NEW."%(field)s",
                    _dlm,
                    _user_id,
                    '~'
                );
            END IF;
            """
            % params
        )
    else:
        raise ValueError('Invalid trigger type: "%s"' % trigger_type)


def get_json_history_sql(trigger_type, table_name, pk_name):
    history_table_name = truncate_long_name(table_name + "_history")
    params = {
        "history_table": "%s.%s" % (conf.SCHEMA_NAME, history_table_name),
        "pk_name": pk_name,
        "user_field": conf.USER_FIELD,
    }
    if trigger_type == "insert":
        return (
            """
            INSERT INTO %(history_table)s (
                %(pk_name)s,
                old_value,
                new_value,
                date_modified,
                %(user_field)s,
                transaction_type
            )
            VALUES (
                NEW.%(pk_name)s,
                NULL,
                row_to_json(NEW),
                _dlm,
                _user_id,
                '+'
            );
            """
            % params
        )
    elif trigger_type == "delete":
        return (
            """
            INSERT INTO %(history_table)s (
                %(pk_name)s,
                old_value,
                new_value,
                date_modified,
                %(user_field)s,
                transaction_type
            )
            VALUES (
                OLD.%(pk_name)s,
                row_to_json(OLD),
                NULL,
                _dlm,
                _user_id,
                '-'
            );
            """
            % params
        )
    elif trigger_type == "update":
        return (
            """
            INSERT INTO %(history_table)s (
                %(pk_name)s,
                old_value,
                new_value,
                date_modified,
                %(user_field)s,
                transaction_type
            )
            VALUES (
                OLD.%(pk_name)s,
                row_to_json(OLD),
                row_to_json(NEW),
                _dlm,
                _user_id,
                '~'
            );
            """
            % params
        )
    else:
        raise ValueError('Invalid trigger type: "%s"' % trigger_type)


def create_trigger(cursor, trigger_type, table_name, pk_name, table_schema="public"):
    """
    Creates a history trigger of the specified type (update, insert, or delete) on the
    specified table.
    """
    assert trigger_type in ("insert", "update", "delete")
    if not table_exists(cursor, table_name, table_schema):
        return
    # First, create the function that the trigger will call for each row.
    body_sql = []
    if conf.USE_JSON:
        body_sql.append(get_json_history_sql(trigger_type, table_name, pk_name))
    else:
        for field_name, field_type in get_table_columns(
            cursor, table_name, table_schema
        ):
            body_sql.append(
                get_field_history_sql(
                    trigger_type, table_name, field_name, field_type, pk_name
                )
            )
    trigger_name = "trig_%s_%s" % (table_name, trigger_type)
    fx_name = truncate_long_name(trigger_name)
    params = {
        "fx_name": fx_name,
        "body": "".join(body_sql),
        "history_user_table": conf.USER_TEMP_TABLE,
        "history_user_field": conf.USER_FIELD,
        "return": "OLD" if trigger_type == "delete" else "NEW",
        "role": conf.DB_ROLE,
        "timestamp_type": "timestamp with time zone"
        if conf.USE_TIMEZONES
        else "timestamp",
        "user_type": conf.USER_TYPE,
        "default_user": maybe_quote(conf.DEFAULT_USER),
        "default_user_error": "true" if conf.DEFAULT_USER_ERROR else "false",
    }
    cursor.execute(
        """
        CREATE OR REPLACE FUNCTION %(fx_name)s() RETURNS trigger AS $BODY$
            DECLARE
                _dlm %(timestamp_type)s := now();
                _user_id %(user_type)s := %(default_user)s;
                _exists boolean;
            BEGIN
                EXECUTE 'select exists (select 1 from information_schema.tables
                    where table_name = ''%(history_user_table)s'')' INTO _exists;
                IF _exists THEN
                    EXECUTE 'select %(history_user_field)s from %(history_user_table)s'
                        INTO _user_id;
                ELSIF %(default_user_error)s THEN
                    RAISE EXCEPTION '%(history_user_table)s does not exist.';
                END IF;
                %(body)s
                RETURN %(return)s;
            END;$BODY$
        LANGUAGE 'plpgsql' VOLATILE;
        ALTER FUNCTION %(fx_name)s() OWNER TO %(role)s;
        GRANT EXECUTE ON FUNCTION %(fx_name)s() TO %(role)s;
        REVOKE ALL ON FUNCTION %(fx_name)s() FROM public;
        """
        % params
    )
    # Now create the actual trigger.
    calling_fx_long = "tr_%s_%s" % (table_name, trigger_type)
    calling_fx = truncate_long_name(calling_fx_long)
    params = {
        "calling_fx": calling_fx,
        "when": "AFTER" if trigger_type == "delete" else "BEFORE",
        "trans_type": trigger_type.upper(),
        "table": table_name,
        "fx_name": fx_name,
    }
    cursor.execute(
        """
        DROP TRIGGER IF EXISTS %(calling_fx)s ON "%(table)s";
        CREATE TRIGGER %(calling_fx)s
            %(when)s %(trans_type)s ON "%(table)s"
            FOR EACH ROW EXECUTE PROCEDURE %(fx_name)s();
    """
        % params
    )


def drop_trigger(cursor, trigger_type, table_name, table_schema="public"):
    calling_fx_long = "tr_%s_%s" % (table_name, trigger_type)
    calling_fx = truncate_long_name(calling_fx_long)
    cursor.execute(
        'DROP TRIGGER IF EXISTS %(calling_fx)s ON "%(table)s";'
        % {
            "calling_fx": calling_fx,
            "table": table_name,
        }
    )
    fx_name_long = "trig_%s_%s" % (table_name, trigger_type)
    fx_name = truncate_long_name(fx_name_long)
    cursor.execute(
        "DROP FUNCTION IF EXISTS %(fx_name)s();"
        % {
            "fx_name": fx_name,
        }
    )
