mport functools
import re
from math import ceil

import falcon
import sqlalchemy
import sqlalchemy.orm
from sqlalchemy import orm, event
from threading import Lock

from sqlalchemy.ext.declarative.api import declarative_base, DeclarativeMeta
from sqlalchemy.orm.exc import UnmappedClassError

from .middleware import DBSessionManagement

_camelcase_re = re.compile(r'([A-Z]+)(?=[a-z0-9])')


__all__ = [
    'BaseQuery',
    'Model',
    'SQLAlchemyManager',
    'Pagination',
    'DBSessionManagement'
]


def _make_table(db):
    def _make_table(*args, **kwargs):
        if len(args) > 1 and isinstance(args[1], db.Column):
            args = (args[0], db.metadata) + args[1:]
        info = kwargs.pop('info', None) or {}
        info.setdefault('bind_key', None)
        kwargs['info'] = info
        return sqlalchemy.Table(*args, **kwargs)

    return _make_table


def _set_default_query_class(d, cls):
    if 'query_class' not in d:
        d['query_class'] = cls


def _wrap_with_default_query_class(fn, cls):
    @functools.wraps(fn)
    def newfn(*args, **kwargs):
        _set_default_query_class(kwargs, cls)
        if "backref" in kwargs:
            backref = kwargs['backref']
            if isinstance(backref, basestring):
                backref = (backref, {})
            _set_default_query_class(backref[1], cls)
        return fn(*args, **kwargs)

    return newfn


def _include_sqlalchemy(obj, query_cls):
    for module in sqlalchemy, sqlalchemy.orm:
        for key in module.__all__:
            if not hasattr(obj, key):
                setattr(obj, key, getattr(module, key))
    # Note: obj.Table does not attempt to be a SQLAlchemy Table class.
    obj.Table = _make_table(obj)
    obj.relationship = _wrap_with_default_query_class(
        obj.relationship, query_cls)
    obj.relation = _wrap_with_default_query_class(
        obj.relation, query_cls)
    obj.dynamic_loader = _wrap_with_default_query_class(
        obj.dynamic_loader, query_cls)
    obj.event = event


def _should_set_tablename(bases, d):
    """Check what values are set by a class and its bases to determine if a
    tablename should be automatically generated.

    The class and its bases are checked in order of precedence: the class
    itself then each base in the order they were given at class definition.

    Abstract classes do not generate a tablename, although they may have set
    or inherited a tablename elsewhere.

    If a class defines a tablename or table, a new one will not be generated.
    Otherwise, if the class defines a primary key, a new name will be generated.

    This supports:

    * Joined table inheritance without explicitly naming sub-models.
    * Single table inheritance.
    * Inheriting from mixins or abstract models.

    :param bases: base classes of new class
    :param d: new class dict
    :return: True if tablename should be set
    """

    if '__tablename__' in d or '__table__' in d or '__abstract__' in d:
        return False

    if any(v.primary_key for v in d.itervalues()
           if isinstance(v, sqlalchemy.Column)):
        return True

    for base in bases:
        if hasattr(base, '__tablename__') or hasattr(base, '__table__'):
            return False

        for name in dir(base):
            attr = getattr(base, name)

            if isinstance(attr, sqlalchemy.Column) and attr.primary_key:
                return True


class _BoundDeclarativeMeta(DeclarativeMeta):
    def __new__(cls, name, bases, d):
        if _should_set_tablename(bases, d):
            def _join(match):
                word = match.group()
                if len(word) > 1:
                    return ('_%s_%s' % (word[:-1], word[-1])).lower()
                return '_' + word.lower()

            d['__tablename__'] = _camelcase_re.sub(_join, name).lstrip('_')

        return DeclarativeMeta.__new__(cls, name, bases, d)


class _QueryProperty(object):
    def __init__(self, sa):
        self.sa = sa

    def __get__(self, obj, type):
        try:
            mapper = orm.class_mapper(type)
            if mapper:
                return type.query_class(mapper, session=self.sa.session())
        except UnmappedClassError:
            return None


class Pagination(object):
    """Internal helper class returned by :meth:`BaseQuery.paginate`.  You
    can also construct it from any other SQLAlchemy query object if you are
    working with other libraries.  Additionally it is possible to pass `None`
    as query object in which case the :meth:`prev` and :meth:`next` will
    no longer work.
    """

    def __init__(self, query, page, per_page, total, items):
        #: the unlimited query object that was used to create this
        #: pagination object.
        self.query = query
        #: the current page number (1 indexed)
        self.page = page
        #: the number of items to be displayed on a page.
        self.per_page = per_page
        #: the total number of items matching the query
        self.total = total
        #: the items for the current page
        self.items = items

    @property
    def pages(self):
        """The total number of pages"""
        if self.per_page == 0:
            pages = 0
        else:
            pages = int(ceil(self.total / float(self.per_page)))
        return pages

    def prev(self, error_out=False):
        """Returns a :class:`Pagination` object for the previous page."""
        assert self.query is not None, 'a query object is required ' \
                                       'for this method to work'
        return self.query.paginate(self.page - 1, self.per_page, error_out)

    @property
    def prev_num(self):
        """Number of the previous page."""
        return self.page - 1

    @property
    def has_prev(self):
        """True if a previous page exists"""
        return self.page > 1

    def next(self, error_out=False):
        """Returns a :class:`Pagination` object for the next page."""
        assert self.query is not None, 'a query object is required ' \
                                       'for this method to work'
        return self.query.paginate(self.page + 1, self.per_page, error_out)

    @property
    def has_next(self):
        """True if a next page exists."""
        return self.page < self.pages

    @property
    def next_num(self):
        """Number of the next page"""
        return self.page + 1

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        """Iterates over the page numbers in the pagination.  The four
        parameters control the thresholds how many numbers should be produced
        from the sides.  Skipped page numbers are represented as `None`.
        This is how you could render such a pagination in the templates:
        """
        last = 0
        for num in xrange(1, self.pages + 1):
            if num <= left_edge or \
                    (num > self.page - left_current - 1 and \
                                 num < self.page + right_current) or \
                            num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


class Model(object):

    query_class = None
    query = None

    repr_attrs = ('id', )
    excluded_columns = frozenset()

    def __repr__(self):
        attrs = ', '.join('{}={!r}'.format(field, getattr(self, field))
                          for field in self.repr_attrs if hasattr(self, field))
        return '<{}.{} ({})>'.format(
            self.__class__.__module__,
            self.__class__.__name__,
            attrs
        )

    def to_dict(self):
        rv = {}
        for key in self.__table__.columns.keys():
            if key in self.excluded_columns:
                continue
            value = getattr(self, key)
            if key == 'id' or '_id' in key:
                # serialize ids to avoid JS overflows or other weird things
                value = str(value)
            rv[key] = value
        return rv


class BaseQuery(orm.Query):
    def paginate(self, page=None, per_page=None, error_out=True):

        if page is None:
            page = 1

        if per_page is None:
            per_page = 20

        if error_out and page < 1:
            raise falcon.HTTPNotFound()

        items = self.limit(per_page).offset((page - 1) * per_page).all()

        if not items and page != 1 and error_out:
            raise falcon.HTTPNotFound()

        # No need to count if we're on the first page and there are fewer
        # items than we expected.
        if page == 1 and len(items) < per_page:
            total = len(items)
        else:
            total = self.order_by(None).count()

        return Pagination(self, page, per_page, total, items)


class SQLAlchemyManager(object):
    Query = None

    def __init__(self, config=None, use_native_unicode=True,
                 session_options=None, query_class=BaseQuery,
                 model_class=Model, metadata=None):

        self._engine_lock = Lock()
        # TODO: this will only support one db
        self._connector = None
        self._config = config or {}
        self._setup_default_options()
        self.use_native_unicode = use_native_unicode
        self.Query = query_class
        self.session = self.create_scoped_session(session_options)
        self.Model = self.make_declarative_base(model_class, metadata)
        _include_sqlalchemy(self, query_class)

    def create_session(self, options):
        return orm.sessionmaker(bind=self.engine, **options)

    def create_scoped_session(self, options=None):
        options = options or {}
        scopefunc = options.pop('scopefunc', None)
        options.setdefault('query_cls', self.Query)
        return orm.scoped_session(
            self.create_session(options), scopefunc=scopefunc)

    @property
    def metadata(self):
        return self.Model.metadata

    @property
    def engine(self):
        with self._engine_lock:
            if not self._connector:
                self._connector = self.make_connector()
            return self._connector.get_engine()

    def make_declarative_base(self, model, metadata=None):
        base = declarative_base(metadata=metadata,
                                cls=model,
                                name='Model',
                                metaclass=_BoundDeclarativeMeta)
        if not getattr(base, 'query_class', None):
            base.query_class = self.Query

        base.query = _QueryProperty(self)
        return base

    def _setup_default_options(self):
        self._config.setdefault('database_uri', 'sqlite://')
        self._config.setdefault('native_unicode', None)
        self._config.setdefault('echo', False)
        self._config.setdefault('pool_size', None)
        self._config.setdefault('pool_timeout', None)
        self._config.setdefault('pool_recycle', None)
        self._config.setdefault('max_overflow', None)

    def get_pool_options(self):
        def _set_default(option_key, config_key):
            value = self._config[config_key]
            if value is not None:
                options[option_key] = value

        options = {'convert_unicode': True}
        for option in ('pool_size', 'pool_timeout', 'pool_recycle',
                       'max_overflow', 'echo'):
            _set_default(option, option)
        return options

    @property
    def config(self):
        return self._config

    @property
    def database_uri(self):
        return self._config['database_uri']

    def make_connector(self):
        return _EngineConnector(self)

    def get_tables(self):
        result = []
        for table in self.Model.metadata.tables.itervalues():
            if ('view' in table.name) or ('vw_' in table.name):
                continue
            else:
                result.append(table)
        return result

    def _execute_for_all_tables(self, operation, skip_tables=False):
        extra = {}
        if not skip_tables:
            tables = self.get_tables()
            extra['tables'] = tables
        op = getattr(self.Model.metadata, operation)
        op(bind=self.engine, **extra)

    def create_all(self):
        self._execute_for_all_tables('create_all')

    def drop_all(self):
        self._execute_for_all_tables('drop_all')

    def reflect(self):
        self._execute_for_all_tables('reflect', skip_tables=True)

    def __repr__(self):
        return '<{} engine={}>'.format(
            self.__class__.__name__, self.database_uri)


class _EngineConnector(object):
    def __init__(self, manager):
        self._manager = manager
        self._lock = Lock()
        self._connected_for = None
        self._engine = None

    def get_engine(self):
        with self._lock:
            uri = self._manager.database_uri
            echo = self._manager.config['echo']
            if (uri, echo) == self._connected_for:
                return self._engine
            options = self._manager.get_pool_options()
            self._engine = rv = sqlalchemy.create_engine(uri, **options)
            self._connected_for = (uri, echo)
            return rv

