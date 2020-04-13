"""
    flask_generic_views.sqlalchemy
    ==============================

    Provides SQLAlchemy based class-based views for Flask inspired by the ones
    in Django.

    :copyright: (c) 2015 Daniel Knell
    :license: BSD, see LICENSE for more information.
"""

from __future__ import absolute_import

from flask import abort, current_app, redirect, request
from flask.ext.sqlalchemy import Pagination
from flask.ext.wtf import Form
from inflection import underscore
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.local import LocalProxy
from wtforms_sqlalchemy.orm import model_form

from flask_generic_views._compat import integer_types
from flask_generic_views.core import (ContextMixin, FormMixin, MethodView,
                                      ProcessFormView, TemplateResponseMixin)


def _touch(obj):
    """Touches an SQL alchemy object to repopulate __dict__ after a commit."""
    for k in inspect(obj).attrs.keys():
        getattr(obj, k, None)
        break


def _find_session():
    return current_app.extensions['sqlalchemy'].db.session


session = LocalProxy(_find_session)


class SingleObjectMixin(ContextMixin):
    """Provides the ability to retrieve an object based on the current HTTP
    request."""
    model = None
    query = None
    slug_field = 'slug'
    context_object_name = None
    slug_view_arg = 'slug'
    pk_view_arg = 'pk'
    query_pk_and_slug = False

    def get_model(self):
        """Retrieve the model used to retrieve the object used by this view.

        By default returns the model associated with :attr:`query` when it's
        set, otherwise it will return :attr:`model`.

        :returns: model
        :rtype: flask_sqlalchemy.Model

        """

        if self.query:
            return self.query._entities[0].entity_zero.class_

        return self.model

    def get_object(self):
        """Retrieve the object used by the view.

        The :class:`~sqlalchemy.orm.query.Query` object from :meth:`get_query`
        will be used as a base query for the object.

        When :attr:`pk_view_arg` exists in the current requests
        :attr:`~flask.Request.view_args` it will be used to filter the query
        by primary-key.

        When :attr:`slug_view_arg` exists in the current requests
        :attr:`~flask.Request.view_args` and either no primary-key was found
        or :attr:`query_pk_and_slug` is ``True`` then it will be used to filter
        the query by :attr:`slug_field`.

        :returns: object
        :rtype: flask_sqlalchemy.Model
        :raises werkzeug.exceptions.NotFound: when no result found

        """
        query = self.get_query()

        pk = request.view_args.get(self.pk_view_arg)
        slug = request.view_args.get(self.slug_view_arg)

        filters = {}

        if pk is None and slug is None:
            error = ('{0} must be called with either object pk or slug')

            raise RuntimeError(error.format(self.__class__.__name__))

        if pk is not None:
            model = self.get_model()
            primary_key = inspect(model).primary_key

            if len(primary_key) > 1:
                error = ('{0} requires non composite primary key')

                raise RuntimeError(error.format(self.__class__.__name__))

            if len(primary_key) == 0:
                error = ('{0} requires primary key')

                raise RuntimeError(error.format(self.__class__.__name__))

            filters[primary_key[0].key] = pk

        if slug is not None and (pk is None or self.query_pk_and_slug):
            slug_field = self.get_slug_field()

            filters[slug_field] = slug

        try:
            return query.filter_by(**filters).one()
        except NoResultFound:
            abort(404)

    def get_query(self):
        """Retrieve the query used to retrieve the object used by this view.

        By default returns :attr:`query` when it's set, otherwise it will
        return a query for :attr:`model`.

        :returns: query
        :rtype: sqlalchemy.orm.query.Query

        """
        if self.query is None and self.model is None:
            error = ("{0} requires either a definition of 'query', 'model', "
                     "or an implementation of 'get_query()'")

            raise NotImplementedError(error.format(self.__class__.__name__))

        if self.query:
            return self.query

        return self.model.query

    def get_slug_field(self):
        """Retrive the name of model field that contains the slug.

        By default it will return :attr:`slug_field`.

        :returns: slug field
        :rtype: str

        """
        return self.slug_field

    def get_context_object_name(self):
        """Retrieve the context variable name that :attr:`object` will be
        stored under.

        By default it will return :attr:`context_object_name`, falling back
        to a name based on the model from :attr:`query` or :attr:`model`, the
        model ``BlogPost`` would have the context object name ``blog_post``.

        :returns: context object name
        :rtype: str

        """
        if self.context_object_name:
            return self.context_object_name

        model = self.get_model()

        if model:
            return underscore(model.__name__)

        return None

    def get_context_data(self, **kwargs):
        """Extends the view context with :attr:`object`.

        When :attr:`object` is set, an ``object``` variable containing
        :attr:`object` is added to the context.

        A variable named with the result of :meth:`get_context_object_name`
        containing :attr:`object` will be added to the context.

        :param kwargs: context
        :type kwargs: dict
        :returns: context
        :rtype: dict

        """
        if hasattr(self, 'object'):
            kwargs.setdefault('object', self.object)

            context_object_name = self.get_context_object_name()
            if context_object_name:
                kwargs.setdefault(context_object_name, self.object)

        return super(SingleObjectMixin, self).get_context_data(**kwargs)


class BaseDetailView(SingleObjectMixin, MethodView):
    """View class to retrieve an object."""

    def get(self, **kwargs):
        """Set :attr:`object` to the result of :meth:`get_object` and
        create a response using the return value of :meth:`get_context_data()`.

        :param kwargs: keyword arguments from url rule
        :type kwargs: dict
        :returns: response
        :rtype: werkzeug.wrappers.Response

        """
        self.object = self.get_object()
        return self.create_response(self.get_context_data())


class SingleObjectTemplateResponseMixin(TemplateResponseMixin):
    """ Creates :class:`~werkzeug.wrappers.Response` instances with a rendered
    template based on the given context.

    When no template names are provided, the class will try and generate one
    based on the model name.

    """
    template_name_field = None
    template_name_suffix = '_detail'

    def _format_template_name(self, name):
        if request.blueprint:
            prefix = '{0}/'.format(request.blueprint)
        else:
            prefix = ''

        return '{0}{1}{2}.html'.format(prefix, name, self.template_name_suffix)

    def get_template_list(self):
        """Retrives a list of template names to use for when rendering the
        template.

        When no
        :attr:`~flask_generic_views.core.TemplateResponseMixin.template_name`
        is set then the following will be provided instead:

        * the value of the :attr:`template_name_field` field on the model when
          availible.

        * A template based on :attr:`template_name_suffix`, the model, and the
          current blueprint. The model ``BlogArticle`` in  blueprint
          ``blogging`` would generate the template name
          ``blogging/blog_article_detail.html``, no blueprint would generate
          ``blog_article_detail.html``

        :returns: list of template names
        :rtype: list

        """
        try:
            names = super(SingleObjectTemplateResponseMixin, self)\
                .get_template_list()
        except NotImplementedError:
            names = []
            obj = getattr(self, 'object', None)

            if self.template_name_field and obj:
                name = getattr(obj, self.template_name_field, None)
                if name:
                    names.append(name)

            model = self.get_model()

            if model:
                name = underscore(model.__name__)
                names.append(self._format_template_name(name))

            if not names:
                raise

        return names


class DetailView(SingleObjectTemplateResponseMixin, BaseDetailView):
    """Renders a given template,, with the context containing an object
    retrieved from the database.

    .. code-block:: python

        class PostDetailView(DetailView):
            model = Post

            def context_data(self, **kwargs):
                kwargs.setdefault('now', datetime.now())

        post_detail = PostDetailView.as_view('post_detail')

        app.add_url_rule('/posts/<pk>', view_func=post_detail)

    The above example will render the ``post_detail.html`` template from a
    folder named after the current blueprint, when no blueprint is used it will
    look in the root template folder. The view context will contain the object
    as ``object`` and the current date-time as ``now``.

    .. code-block:: python

        post_detail = DetailView.as_view('post_detail', model=Post)

        app.add_url_rule('/post/<pk>', view_func=post_detail)

    It can also be used directly in a URL rule to avoid having to create
    additional classes.

    .. code-block:: jinja

        {# post_detail.html #}
        <h1>{{ object.title }}</h1>
        <p>{{ object.body }}</p>
        <p>Published: {{ object.published_at }}</p>
        <p>Date: {{ now }}</p>

    """


class MultipleObjectMixin(ContextMixin):
    """Provides the ability to retrieve a list of objects based on the current
    HTTP request.

    If :attr:`paginate_by` is specified, the object list will be paginated. You
    can specify the page number in the URL in one of two ways:

    * Pass the page as a view argument in the url rule.

      ::

          post_list = PostListView.as_view('post_list')

          app.add_url_rule('/posts/page/<int:page>', view_func=post_list)

    * Pass the page as a query-string argument in the request url.

      ::

          /posts?page=5

    When no page is provided it defaults to 1.

    When :attr:`error_out` is set, a non numeric page number or empty page
    (other than the first page) will result in a
    :exc:`~werkzeug.exceptions.NotFound` exception.

    """

    error_out = False
    query = None
    model = None
    per_page = None
    context_object_name = None
    pagination_class = Pagination
    page_arg = 'page'
    order_by = None

    def get_model(self):
        """Retrieve the model used to retrieve the object used by this view.

        By default returns the model associated with :attr:`query` when it's
        set, otherwise it will return :attr:`model`.

        :returns: model
        :rtype: flask_sqlalchemy.Model

        """
        if self.query:
            return self.query._entities[0].entity_zero.class_

        return self.model

    def get_page(self, error_out):
        """Retrieve the current page number.

        The page is first checked for in the view keyword arguments, and then
        the query-string arguments using the key from :attr:`page_arg`.

        When the value is not a an unsigned integer greater than zero and
        ``error_out`` is ``True`` then a :exc:`~werkzeug.exceptions.NotFound`
        exception will be raised. When ``False`` the page will default to 1.

        :param error_out: raise error on invalid page number
        :type error_out: bool
        :returns: number of items per page
        :rtype: int

        """
        page_arg = self.page_arg
        page = request.view_args.get(page_arg, request.args.get(page_arg, 1))

        try:
            page = int(page)
        except ValueError:
            pass
        finally:
            if not isinstance(page, integer_types) or page < 1:
                if error_out:
                    abort(404)
                else:
                    page = 1

        return page

    def get_query(self):
        """Retrieve the query used to retrieve the object used by this view.

        By default returns :attr:`query` when it's set, otherwise it will
        return a query for :attr:`model`.

        :returns: query
        :rtype: flask_sqlalchemy.BaseQuery

        """
        if self.query is None and self.model is None:
            error = ("{0} requires either a definition of 'query', 'model', "
                     "or an implementation of 'get_query()'")

            raise NotImplementedError(error.format(self.__class__.__name__))

        if self.query:
            query = self.query
        else:
            query = self.model.query

        order_by = self.get_order_by()

        if order_by:
            query = query.order_by(*order_by)

        return query

    def get_order_by(self):
        """Retrieve a :class:`tuple` of criteria to pass to pass to the query
        :meth:`~sqlalchemy.orm.query.Query.order_by` method.

        :returns: list of order by criteria
        :rtype: list

        """
        return self.order_by

    def apply_pagination(self, object_list, per_page, error_out):
        """Retrieves a 3-item tuple containing (pagination, object_list,
        is_paginated).

        The ``pagination`` from :meth:`get_pagination`, The ``object_list``
        paginated with page from :meth:`get_page` and ``per_page``, and
        wether there is more than one page will be returned.

        When ``error_out`` is set then a :exc:`~werkzeug.exceptions.NotFound`
        exception will be raised when the page number is invalid, or refers
        to an empty page greater than 1.

        :param query: sqlalchemy query
        :type query: flask_sqlalchemy.BaseQuery
        :param per_page: items per page
        :type per_page: int
        :param error_out: error out
        :type error_out: bool
        :returns: pagination instance, object list, is paginated
        :rtype: tuple
        :raises werkzeug.exceptions.NotFound: when page number is invalid
        """
        page = self.get_page(error_out)

        items = object_list.limit(per_page).offset((page - 1) * per_page).all()

        if not items and page != 1 and error_out:
            abort(404)

        if page == 1 and len(items) < per_page:
            total = len(items)
        else:
            total = object_list.order_by(None).count()

        result = self.get_pagination(
            object_list, page, per_page, total, items)

        return (result, result.items, result.pages > 1)

    def get_per_page(self):
        """Retrieve the number of items to show per page.

        By default returns :attr:`per_page`.

        :returns: number of items per page
        :rtype: int

        """
        return self.per_page

    def get_pagination(self, query, page, per_page, total, items):
        """
        :param query: sqlalchemy query
        :type query: flask_sqlalchemy.BaseQuery
        :param page: page number
        :type page: int
        :param per_page: items per page
        :type per_page: int
        :param total: total items
        :type total: int
        :param items: list of objects
        :type items: list
        :returns: pagination instance
        :rtype: flask_sqlalchemy.Pagination
        """
        return self.pagination_class(query, page, per_page, total, items)

    def get_error_out(self):
        """Retrive how invalid page numbers or empty pages are handled.

        When ``True`` a :exc:`werkzeug.exceptions.NotFound` will be raised for
        invalid page numbers or empty pages greater than one.

        When ``False`` invalid page numbers will default to 1 and empty pages
        will be rendered with an empty ``object_list``.

        By default returns :attr:`error_out`.

        :returns: error out
        :rtype: bool

        """
        return self.error_out

    def get_context_object_name(self):
        """Retrieve the context variable name that :attr:`object` will be
        stored under.

        By default it will return :attr:`context_object_name`, falling back
        to a name based on the model from :attr:`query` or :attr:`model`, the
        model ``BlogPost`` would have the context object name
        ``blog_post_list``.

        :returns: context object name
        :rtype: str

        """
        if self.context_object_name:
            return self.context_object_name

        model = self.get_model()

        if model:
            return '{0}_list'.format(underscore(model.__name__))

        return None

    def get_context_data(self, **kwargs):
        """Extends the view context with :attr:`object`.

        When the return value of :meth:`get_per_page` is not ``None``, then
        :attr:`object_list` will be paginated with :meth:`apply_pagination`
        and the resulting ``pagination``, ``object_list`` and ``is_paginated``
        will be stored in the view context. Otherwise the result of executing
        :attr:`object_list` will be stored in ``object_list``, ``pagination``
        will be ``None``, and ``is_paginated`` will be ``False``.

        A variable named with the result of :meth:`get_context_object_name`
        containing ``object_list`` will be added to the context.

        :param kwargs: context
        :type kwargs: dict
        :returns: context
        :rtype: dict

        """
        query = self.object_list

        per_page = self.get_per_page()
        error_out = self.get_error_out()

        if per_page:
            paginated = self.apply_pagination(query, per_page, error_out)

            pagination, object_list, is_paginated = paginated
        else:
            pagination, object_list, is_paginated = None, query.all(), False

        kwargs.setdefault('pagination', pagination)
        kwargs.setdefault('object_list', object_list)
        kwargs.setdefault('is_paginated', is_paginated)

        context_object_name = self.get_context_object_name()

        if context_object_name is not None:
            kwargs.setdefault(context_object_name, object_list)

        return super(MultipleObjectMixin, self).get_context_data(**kwargs)


class BaseListView(MultipleObjectMixin, MethodView):
    """View class to retrieve a list of objects."""

    def get(self, **kwargs):
        """Set :attr:`object_list` to the result of :meth:`get_query` and
        create a view from the context.

        :param kwargs: keyword arguments from url rule
        :type kwargs: dict
        :returns: response
        :rtype: werkzeug.wrappers.Response

        """
        self.object_list = self.get_query()

        return self.create_response(self.get_context_data())


class MultipleObjectTemplateResponseMixin(TemplateResponseMixin):
    template_name_suffix = '_list'

    def _format_template_name(self, name):
        if request.blueprint:
            prefix = '{0}/'.format(request.blueprint)
        else:
            prefix = ''

        return '{0}{1}{2}.html'.format(prefix, name, self.template_name_suffix)

    def get_template_list(self):
        """Retrives a list of template names to use for when rendering the
        template.

        When no
        :attr:`~flask_generic_views.core.TemplateResponseMixin.template_name`
        is set then the following will be provided instead:

        * A template based on :attr:`template_name_suffix`, the model, and the
          current blueprint. The model ``BlogArticle`` in  blueprint
          ``blogging`` would generate the template name
          ``blogging/blog_article_list.html``, no blueprint would generate
          ``blog_article_list.html``

        :returns: list of template names
        :rtype: list

        """
        try:
            names = super(MultipleObjectTemplateResponseMixin, self)\
                .get_template_list()
        except NotImplementedError:
            names = []

            model = self.get_model()

            if model:
                name = underscore(model.__name__)
                names.append(self._format_template_name(name))

            if not names:
                raise

        return names


class ListView(MultipleObjectTemplateResponseMixin, BaseListView):
    """Renders a given template,, with the context containing a list of objects
    retrieved from the database.

    .. code-block:: python

        class PostListView(DetailView):
            model = Post

            def context_data(self, **kwargs):
                kwargs.setdefault('now', datetime.now())

        post_list = PostDetailView.as_view('post_list')

        app.add_url_rule('/posts', view_func=post_list)

    The above example will render the ``post_list.html`` template from a folder
    named after the current blueprint, when no blueprint is used it will look
    in the root template folder. The view context will contain the list of
    objects as ``post_list`` and the current date-time as ``now``.

    .. code-block:: python

        post_list = ListView.as_view('post_list', model=Post)

        app.add_url_rule('/posts', view_func=post_list)

    It can also be used directly in a URL rule to avoid having to create
    additional classes.

    .. code-block:: jinja

        {# post_list.html #}
        <ul>
        {% for post in object_list  %}
          <li>{{ post.title }}</li>
        {% else %}
          <li>No posts found.</li>
        {% endfor %}
        </ul>

    """


class ModelFormMixin(FormMixin, SingleObjectMixin):
    fields = None

    def get_form_class(self):
        """Retrieve the form class to instantiate.

        When :attr:`form_class` is not set, a form class will be automatically
        generated using :attr:`model` and :attr:`fields`.

        :returns: form class
        :rtype: type

        """
        if self.fields is not None and self.form_class:
            error = ("{0} requires either a definition of 'fields' or "
                     "'form_class', not both")

            raise RuntimeError(error.format(self.__class__.__name__))

        if self.form_class:
            return self.form_class

        if self.fields is None:
            error = ("{0} requires a definition of 'fields' when "
                     "'form_class' is not defined")

            raise NotImplementedError(error.format(self.__class__.__name__))

        return model_form(self.get_model(), session, Form, self.fields)

    def get_form_kwargs(self):
        """Extends the form keyword arguments with `obj`
        containing :attr:`object` when set.

        :returns: keyword arguments
        :rtype: dict

        """
        kwargs = super(ModelFormMixin, self).get_form_kwargs()

        if hasattr(self, 'object'):
            kwargs['obj'] = self.object

        return kwargs

    def get_success_url(self):
        """Retrive the URL to redirect to when the form is successfully
        validated.

        By default returns :attr:`success_url` after being interpolated with
        the object attributes using :meth:`~str.format`. So ``"/posts/{id}"``
        will be populated with ``self.object.id``

        :returns: URL
        :rtype: str

        """
        if self.success_url is None:
            error = ("{0} requires either a definition of 'success_url' or "
                     "an implementation of 'get_success_url()'")

            raise NotImplementedError(error.format(self.__class__.__name__))

        return self.success_url.format(**self.object.__dict__)

    def form_valid(self, form):
        """Creates or updates :attr:`object` from :attr:`model`, persists it to
        database, and redirects to :meth:`get_success_url`.

        :param form: form instance
        :type form: flask_wtf.Form
        :returns: response
        :rtype: werkzeug.wrappers.Response

        """
        if not hasattr(self, 'object'):
            self.object = self.model()
            session.add(self.object)

        form.populate_obj(self.object)

        session.commit()

        _touch(self.object)

        return super(ModelFormMixin, self).form_valid(form)


class BaseCreateView(ModelFormMixin, ProcessFormView):
    """View class for creating an object."""


class CreateView(SingleObjectTemplateResponseMixin, BaseCreateView):
    """View class to display a form for creating an object. When invalid it
    shows the form with validation errors, when valid it saves a new object to
    the database and redirects to a new URL.

    .. code-block:: python

        class PostCreateView(FormView):
            model = Post
            fields = ('title', 'body')
            success_url = '/posts/{id}'

        post_create = PostCreateView.as_view('post_create')

        app.add_url_rule('/posts/new', view_func=post_create)

    The above example will render the template ``post_form.html`` with an
    instance of :class:`flask_wtf.Form` in the context variable ``form`` with
    fields based on :attr:`~ModelFormView.fields` and
    :attr:`ModelFormView.model`, when the user submits the form with valid data
    an instance of Post will be saved to the database, and the user redirected
    to its page, when the form is submitted with  invalid data
    ``post_form.html`` will be rendered again, and the form will contain any
    error messages.

    .. code-block:: python

        post_create = CreateView.as_view('post_create', model=Post,
                                         fields=('title', 'body'),
                                         success_url = '/posts/{id}')

        app.add_url_rule('/posts/new', view_func=post_create)

    It can also be used directly in a URL rule to avoid having to create
    additional classes.

    .. code-block:: jinja

        {# post_form.html #}
        <form action="" method="post">
          <p>{{ form.title.label }} {{ form.title }}</p>
          <p>{{ form.title.label }} {{ form.title }}</p>
          <input type="submit" value="Save">
        </form>

    """
    template_name_suffix = '_form'


class BaseUpdateView(ModelFormMixin, ProcessFormView):
    """View class for updating an object."""

    def get(self, **kwargs):
        """Set :attr:`object` to the result of :meth:`get_object` and
        create a response using the return value of :meth:`get_context_data()`.

        :param kwargs: keyword arguments from url rule
        :type kwargs: dict
        :returns: response
        :rtype: werkzeug.wrappers.Response

        """
        self.object = self.get_object()
        return super(BaseUpdateView, self).get(**kwargs)

    def post(self, **kwargs):
        """Set :attr:`object` to the result of :meth:`get_object` and
        construct and validates a form.

        When the form is valid :meth:`form_valid` is called, when the form
        is invalid :meth:`form_invalid` is called.

        :param kwargs: keyword arguments from url rule
        :type kwargs: dict
        :returns: response
        :rtype: werkzeug.wrappers.Response

        """
        self.object = self.get_object()
        return super(BaseUpdateView, self).post(**kwargs)


class UpdateView(SingleObjectTemplateResponseMixin, BaseUpdateView):
    """View class to display a form for updating an object. When invalid it
    shows the form with validation errors, when valid it saves the updated
    object to the database and redirects to a new URL.

    .. code-block:: python

        class PostUpdateView(FormView):
            model = Post
            fields = ('title', 'body')
            success_url = '/posts/{id}'

        post_update = PostUpdateView.as_view('post_update')

        app.add_url_rule('/posts/new', view_func=post_update)

    The above example will render the template ``post_form.html`` with an
    instance of :class:`flask_wtf.Form` in the context variable ``form`` with
    fields based on :attr:`~ModelFormView.fields` and
    :attr:`ModelFormView.model`, when the user submits the form with valid data
    an instance of Post will be updated in the database, and the user
    redirected to its page, when the form is submitted with  invalid data
    ``post_form.html`` will be rendered again, and the form will contain any
    error messages.

    .. code-block:: python

        post_update = UpdateView.as_view('post_update', model=Post,
                                         fields=('title', 'body'),
                                         success_url = '/posts/{id}')

        app.add_url_rule('/posts/<pk>/edit', view_func=post_update)

    It can also be used directly in a URL rule to avoid having to create
    additional classes.

    .. code-block:: jinja

        {# post_form.html #}
        <form action="" method="post">
          <p>{{ form.title.label }} {{ form.title }}</p>
          <p>{{ form.title.label }} {{ form.title }}</p>
          <input type="submit" value="Save">
        </form>

    """
    template_name_suffix = '_form'


class DeletionMixin(object):
    """Handle the DELETE http method."""

    success_url = None

    def delete(self, **kwargs):
        """Set :attr:`object` to the result of :meth:`get_object`,
        delete the object from the database, and create a response using the
        return value of :meth:`get_context_data()`.

        :param kwargs: keyword arguments from url rule
        :type kwargs: dict
        :returns: response
        :rtype: werkzeug.wrappers.Response

        """
        self.object = self.get_object()
        session.delete(self.object)
        session.commit()
        _touch(self.object)
        return redirect(self.get_success_url())

    def post(self, **kwargs):
        """Passes all keyword arguments to :meth:`delete`.

        :param kwargs: keyword arguments from url rule
        :type kwargs: dict
        :returns: response
        :rtype: werkzeug.wrappers.Response

        """
        return self.delete(**kwargs)

    def get_success_url(self):
        """Retrive the URL to redirect to when the form is successfully
        validated.

        By default returns :attr:`success_url` after being interpolated with
        the object attributes using :meth:`~str.format`. So ``"/posts/{id}"``
        will be populated with ``self.object.id``

        :returns: URL
        :rtype: str

        """
        if self.success_url is None:
            error = ("{0} requires either a definition of 'success_url' or "
                     "an implementation of 'get_success_url()'")

            raise NotImplementedError(error.format(self.__class__.__name__))

        return self.success_url.format(**self.object.__dict__)
        if self.success_url is None:
            error = ("{0} requires either a definition of 'success_url' or "
                     "an implementation of 'get_success_url()'")

            raise NotImplementedError(error.format(self.__class__.__name__))

        return self.success_url.format(**self.object.__dict__)


class BaseDeleteView(DeletionMixin, BaseDetailView):
    """View class for deleting an object."""

    methods = ['GET', 'POST', 'DELETE']


class DeleteView(SingleObjectTemplateResponseMixin, BaseDeleteView):
    """Displays a confirmation page and deletes an existing object. The object
    will ve deleted on POST or DELETE requests, for GET requests a conformation
    page will be shown which should contain a form to POST to the same URL.

    ::

        class PostDeleteView(DeleteView):
            model = Post
            success_url = "/posts"

        post_delete = PostDeleteView.as_view('post_delete')

        app.add_url_rule('/posts/<id>', view_func=post_delete)

    The above will render ``post_delete.html`` when accessed by GET request,
    for a POST or DELETE request an instance will be deleted from the database
    and the user redirected to ``/posts``.

    ::

        post_delete = DeleteView.as_view('post_delete', model=Post,
                                         success_url = '/posts')

        app.add_url_rule('/posts/<id>/delete', view_func=post_delete)

    It can also be used directly in a URL rule to avoid having to create
    additional classes.

    .. code-block:: jinja

        {# post_form.html #}
        <form action="" method="post">
          <p>Are you sure you want to delete "{{ object }}"?</p>
          <input type="submit" value="Delete">
        </form>

    """
    template_name_suffix = '_delete'
