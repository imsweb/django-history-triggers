from django.core.management.base import BaseCommand
from django.db import connections, transaction
from django.conf import settings
from optparse import make_option

HISTORY_SCHEMA_NAME = getattr(settings, 'HISTORY_SCHEMA', 'history')
HISTORY_USER_TEMP_TABLE = getattr(settings, 'HISTORY_USER_TEMP_TABLE', 'history_user')
HISTORY_USER_FIELD = getattr(settings, 'HISTORY_USER_FIELD', 'user_id')

# The database role that should own the history tables and triggers.
DB_ROLE = getattr(settings, 'HISTORY_DB_ROLE', settings.DATABASES['default']['USER'])

# Base tables which do not get history attached.
IGNORED_TABLES = getattr(settings, 'HISTORY_IGNORED_TABLES', [])
IGNORED_PREFIXES = getattr(settings, 'HISTORY_IGNORED_PREFIXES', ['django_', 'auth_', 'south_'])

# Columns which should not be tracked in history tables.
IGNORED_TYPES = getattr(settings, 'HISTORY_IGNORED_TYPES', ['bytea'])
IGNORED_COLUMNS = getattr(settings, 'HISTORY_IGNORED_COLUMNS', [])

# Controls the column type for the date_modified field on history tables.
USE_TIMEZONES = getattr(settings, 'HISTORY_USE_TIMEZONES', True)

class Command (BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--drop',
            action='store_true',
            dest='drop',
            default=False,
            help='Drop triggers instead of creating them'),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        cursor = connections['default'].cursor()
        dropping = options.get('drop', False)
        if not dropping:
            create_history_schema(cursor)
        table_names = get_base_tables(cursor)
        for table_name in sorted(table_names):
            pk_name, pk_type = table_names[table_name]
            if not dropping and create_history_table(cursor, table_name, pk_name, pk_type):
                print 'Created history table for %s (pk=%s)' % (table_name, pk_name)
            for trigger_type in ('insert', 'update', 'delete'):
                if dropping:
                    drop_trigger(cursor, trigger_type, table_name)
                else:
                    create_trigger(cursor, trigger_type, table_name, pk_name)

def schema_exists(cursor, schema_name):
    """
    Returns whether or not a schema exists in the DB given the schema name.
    """
    cursor.execute("""
        SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = %s)
    """, (schema_name,))
    return cursor.fetchone()[0]

def table_exists(cursor, table_name, schema_name='public'):
    """
    Returns whether or not a table exists in the DB given the table and schema name (default 'public').
    """
    cursor.execute("""
        SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s AND table_schema = %s)
    """, (table_name, schema_name))
    return cursor.fetchone()[0]

def trigger_exists(cursor, trigger_name, schema_name='public'):
    """
    Returns whether or not the trigger function exists in the DB.
    """
    cursor.execute("""
        SELECT EXISTS (SELECT 1 FROM information_schema.triggers WHERE trigger_schema = %s AND trigger_name = %s)
    """, (schema_name, trigger_name))
    return cursor.fetchone()[0]

def get_base_tables(cursor, schema_name='public'):
    """
    Returns all of the tables in the public schema which are not lkups and not in the exclude list.
    """
    cursor.execute("""
        SELECT t.table_name, COALESCE(kcu.column_name, ''), c.data_type, c.character_maximum_length FROM information_schema.tables t
        LEFT OUTER JOIN information_schema.table_constraints tc ON
            tc.table_schema = t.table_schema AND tc.table_name = t.table_name AND tc.constraint_type = 'PRIMARY KEY'
        LEFT OUTER JOIN information_schema.key_column_usage kcu ON
            kcu.table_schema = tc.table_schema AND kcu.table_name = tc.table_name AND kcu.constraint_name = tc.constraint_name
        LEFT OUTER JOIN information_schema.columns c ON
            c.table_schema = kcu.table_schema AND c.table_name = kcu.table_name AND c.column_name = kcu.column_name
        WHERE t.table_schema = %s AND t.table_type != 'VIEW'
    """, (schema_name,))
    table_names = {}
    for row in cursor.fetchall():
        name = row[0].strip().lower()
        valid = True
        if name in IGNORED_TABLES:
            valid = False
        for prefix in IGNORED_PREFIXES:
            if name.startswith(prefix):
                valid = False
        # Ignore tables without a PRIMARY KEY defined.
        if not row[1].strip():
            valid = False
        if valid:
            pk_type = row[2]
            # Add maximum length if pk_type is character varying.
            if row[3]:
                pk_type += '(%s)' % (row[3])
            table_names[row[0]] = (row[1], pk_type)
    return table_names

def get_table_columns(cursor, table_name, schema_name='public'):
    """
    Returns a list of columns for the given table but excludes text and binary columns
    as well as any column named date_modified or date_last_modified since we don't track
    history for those.
    """
    params = {
        'schema': schema_name,
        'table': table_name,
    }
    cursor.execute("""
        SELECT
            column_name,
            CASE WHEN data_type = 'USER-DEFINED' THEN udt_name ELSE data_type END
        FROM information_schema.columns
        WHERE table_schema = '%(schema)s' AND table_name = '%(table)s'
        ORDER BY column_name
    """ % params)
    for row in cursor.fetchall():
        if row[1].lower() in IGNORED_TYPES:
            continue
        if row[0].lower() in IGNORED_COLUMNS:
            continue
        if '%s.%s' % (table_name, row[0].lower()) in IGNORED_COLUMNS:
            continue
        yield row[0], row[1]

def create_history_schema(cursor):
    """
    Create the history schema if it doesn't already exist.
    """
    if not schema_exists(cursor, HISTORY_SCHEMA_NAME):
        params = {'name': HISTORY_SCHEMA_NAME, 'role': DB_ROLE}
        cursor.execute("""
            CREATE SCHEMA %(name)s AUTHORIZATION %(role)s;
            GRANT ALL ON SCHEMA %(name)s TO %(role)s;
            REVOKE ALL ON SCHEMA %(name)s FROM public;
        """ % params)

def create_history_table(cursor, base_table, pk_name, pk_type):
    """
    Builds the history table (if it doesn't already exist) given the base table name.
    """
    history_table = base_table + '_history'
    if not table_exists(cursor, history_table, HISTORY_SCHEMA_NAME):
        params = {
            'schema': HISTORY_SCHEMA_NAME,
            'table': history_table,
            'role': DB_ROLE,
            'timestamp_type': 'timestamp with time zone' if USE_TIMEZONES else 'timestamp',
            'pk_name': pk_name,
            'pk_type': pk_type,
        }
        cursor.execute("""
            CREATE TABLE %(schema)s.%(table)s (
                %(pk_name)s %(pk_type)s not null,
                field_name varchar(64) not null,
                old_value text,
                new_value text,
                date_modified %(timestamp_type)s not null,
                user_id integer,
                transaction_type char(1) not null
            );
            ALTER TABLE %(schema)s.%(table)s OWNER TO %(role)s;
            REVOKE ALL ON TABLE %(schema)s.%(table)s FROM %(role)s;
            GRANT INSERT, SELECT ON TABLE %(schema)s.%(table)s TO %(role)s;
        """ % params)
        return True
    return False

def get_field_history_sql(trigger_type, table_name, field_name, field_type, pk_name):
    params = {
        'field': field_name,
        'history_table': '%s.%s_history' % (HISTORY_SCHEMA_NAME, table_name),
        'pk_name': pk_name,
    }
    if trigger_type == 'insert':
        return """
                -- %(field)s
                INSERT INTO %(history_table)s (%(pk_name)s, field_name, old_value, new_value, date_modified, user_id, transaction_type)
                VALUES (NEW.%(pk_name)s, '%(field)s', NULL, NEW."%(field)s", _dlm, _user_id, '+');
        """ % params
    elif trigger_type == 'delete':
        return """
                -- %(field)s
                INSERT INTO %(history_table)s (%(pk_name)s, field_name, old_value, new_value, date_modified, user_id, transaction_type)
                VALUES (OLD.%(pk_name)s, '%(field)s', OLD."%(field)s", NULL, _dlm, _user_id, '-');
        """ % params
    elif trigger_type == 'update':
        return """
                -- %(field)s
                IF (OLD."%(field)s" IS DISTINCT FROM NEW."%(field)s") THEN
                    INSERT INTO %(history_table)s (%(pk_name)s, field_name, old_value, new_value, date_modified, user_id, transaction_type)
                    VALUES (OLD.%(pk_name)s, '%(field)s', OLD."%(field)s", NEW."%(field)s", _dlm, _user_id, '~');
                END IF;
        """ % params
    else:
        raise ValueError('Invalid trigger type: "%s"' % trigger_type)

def create_trigger(cursor, trigger_type, table_name, pk_name, table_schema='public'):
    """
    Creates a history trigger of the specified type (update, insert, or delete) on the specified table.
    """
    assert trigger_type in ('insert', 'update', 'delete')
    if not table_exists(cursor, table_name, table_schema):
        return
    # First, create the function that the trigger will call for each row.
    body_sql = []
    for field_name, field_type in get_table_columns(cursor, table_name, table_schema):
        sql = get_field_history_sql(trigger_type, table_name, field_name, field_type, pk_name)
        body_sql.append(sql)
    trigger_name = "trig_%s_%s" % (table_name, trigger_type)
    params = {
        'fx_name': trigger_name,
        'body': ''.join(body_sql),
        'history_user_table': HISTORY_USER_TEMP_TABLE,
        'history_user_field': HISTORY_USER_FIELD,
        'return': 'OLD' if trigger_type == 'delete' else 'NEW',
        'role': DB_ROLE,
        'timestamp_type': 'timestamp with time zone' if USE_TIMEZONES else 'timestamp'
    }
    cursor.execute("""
        CREATE OR REPLACE FUNCTION %(fx_name)s() RETURNS trigger AS $BODY$
            DECLARE
                _dlm %(timestamp_type)s := now();
                _user_id integer := 0;
                _exists boolean;
            BEGIN
                EXECUTE 'select exists (select 1 from information_schema.tables where table_name = ''%(history_user_table)s'')' INTO _exists;
                IF _exists THEN
                    EXECUTE 'select %(history_user_field)s from %(history_user_table)s' INTO _user_id;
                END IF;
                %(body)s
                RETURN %(return)s;
            END;$BODY$
        LANGUAGE 'plpgsql' VOLATILE;
        ALTER FUNCTION %(fx_name)s() OWNER TO %(role)s;
        GRANT EXECUTE ON FUNCTION %(fx_name)s() TO %(role)s;
        REVOKE ALL ON FUNCTION %(fx_name)s() FROM public;
    """ % params)
    # Now create the actual trigger.
    params = {
        'calling_fx': 'tr_%s_%s' % (table_name, trigger_type),
        'when': 'AFTER' if trigger_type == 'delete' else 'BEFORE',
        'trans_type': trigger_type.upper(),
        'table': table_name,
        'trigger_fx': trigger_name,
    }
    cursor.execute("""
        DROP TRIGGER IF EXISTS %(calling_fx)s ON "%(table)s";
        CREATE TRIGGER %(calling_fx)s
            %(when)s %(trans_type)s ON "%(table)s"
            FOR EACH ROW EXECUTE PROCEDURE %(trigger_fx)s();
    """ % params)

def drop_trigger(cursor, trigger_type, table_name, table_schema='public'):
    cursor.execute('DROP TRIGGER IF EXISTS %(calling_fx)s ON "%(table)s";' % {
        'calling_fx': 'tr_%s_%s' % (table_name, trigger_type),
        'table': table_name,
    })
    cursor.execute('DROP FUNCTION IF EXISTS %(fx_name)s();' % {
        'fx_name': 'trig_%s_%s' % (table_name, trigger_type),
    })
