"""
    flask_generic_views.core
    ========================

    Provides database independent class-based views for Flask inspired by the
    ones in Django.

    :copyright: (c) 2015 Daniel Knell
    :license: BSD, see LICENSE for more information.
"""

from flask import Response, abort, redirect, render_template, request, url_for
from flask.views import MethodView as BaseMethodView
from flask.views import View as BaseView
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.routing import BuildError
from werkzeug.urls import url_parse

from flask_generic_views._compat import iteritems


class View(BaseView):
    """ The master class-based base view.

    All other generic views inherit from this base class. This class itself
    inherits from :class:`flask.views.View` and adds a generic constructor,
    that will convert any keyword arguments to instance attributes.

    .. code-block:: python

        class GreetingView(View):
            greeting = 'Hello'

            def dispatch_request(self):
                return "{} World!".format(self.greeting)

        bonjour_view = GreetingView.as_view('bonjour', greeting='Bonjour')

        app.add_url_rule('/bonjour, view_func=bonjour_view)

    The above example shows a generic view that allows us to change the
    greeting while setting up the URL rule.
    """

    def __init__(self, **kwargs):
        for k, v in iteritems(kwargs):
            setattr(self, k, v)


class MethodView(BaseMethodView, View):
    """View class that routes to methods based on HTTP verb.

    This view allows us to break down logic based on the HTTP verb used, and
    avoid conditionals in our code.

    .. code-block:: python

        class GreetingView(View):
            greeting = 'Hello'

            def get(self):
                return "{} World!".format(self.greeting)

            def post(self):
                name = request.form.get('name', 'World')

                return "{} {}!".format(self.greeting, name)

        bonjour_view = GreetingView.as_view('bonjour', greeting='Bonjour')

        app.add_url_rule('/bonjour, view_func=bonjour_view)

    The above example will process the request differently depending on wether
    it was a HTTP POST or GET.

    """


class ContextMixin(object):
    """Default handling of view context data any mixins that modifies the views
    context data should inherit from this class.

    .. code-block:: python

        class RandomMixin(ContextMixin):
            def get_context_data(self, **kwargs):
                kwargs.setdefault('number', random.randrange(1, 100))

                return super(RandomMixin, self).get_context_data(**kwargs)

    """

    def get_context_data(self, **kwargs):
        """Returns a dictionary representing the view context. Any keyword
        arguments provided will be included in the returned context.

        The context of all class-based views will include a ``view`` variable
        that points to the :class:`View` instance.

        :param kwargs: context
        :type kwargs: dict
        :returns: context
        :rtype: dict

        """
        kwargs.setdefault('view', self)

        return kwargs


class TemplateResponseMixin(object):
    """Creates :class:`~werkzeug.wrappers.Response` instances with a rendered
    template based on the given context. The choice of template is configurable
    and can be customised by subclasses.

    .. code-block:: python

        class RandomView(TemplateResponseMixin, MethodView):
            template_name = 'random.html'

            def get(self):
                context = {'number': random.randrange(1, 100)}
                return self.create_response(context)

        random_view = RandomView.as_view('random')

        app.add_url_rule('/random, view_func=random_view)

    """
    template_name = None
    response_class = Response
    mimetype = None

    def create_response(self, context=None, **kwargs):
        """Returns a :attr:`response_class` instance containing the rendered
        template.

        If any keyword arguments are provided, they will be passed to the
        constructor of the response class.

        :param context: context for template
        :type context: dict
        :param kwargs: response keyword arguments
        :type kwargs: dict
        :returns: response
        :rtype: werkzeug.wrappers.Response

        """
        kwargs.setdefault('mimetype', self.mimetype)

        template_names = self.get_template_list()

        response = render_template(template_names, **context)

        return self.response_class(response, **kwargs)

    def get_template_list(self):
        """Returns a list of template names to use for when rendering the
        template.

        The default implementation will return a list containing
        :attr:`template_name`, when not specified a :exc:`NotImplementedError`
        exception will be raised.

        :returns: template list
        :rtype: list
        :raises NotImplementedError: when :attr:`template_name` is not set

        """
        if self.template_name is None:
            error = ("{0} requires either a definition of 'template_name' or "
                     "an implementation of 'get_template_list()'")

            raise NotImplementedError(error.format(self.__class__.__name__))

        return [self.template_name]


class TemplateView(TemplateResponseMixin, ContextMixin, MethodView):
    """Renders a given template, with the context containing parameters
    captured by the URL rule.

    .. code-block:: python

        class AboutView(View):
            template_name = 'about.html'

            def get_context_data(self, **kwargs):
                kwargs['staff'] = ('John Smith', 'Jane Doe')

                return super(AboutView, self).get_context_data(self, **kwargs)

        app.add_url_rule('/about', view_func=AboutView.as_view('about'))


    The :class:`~flask_generic_views.views.TemplateView` can be subclassed to
    create custom views that render a template.

    .. code-block:: python

        about_view = TemplateView.as_view('about', template_name='about.html')

        app.add_url_rule('/about', view_func=about_view,  defaults={
            'staff': ('John Smith', 'Jane Doe')
        })


    It can also be used directly in a URL rule to avoid having to create
    additional classes.

    """

    def get(self, **kwargs):
        """Handle request and return a template response.

        Any keyword arguments will be passed to the views context.

        :param kwargs: keyword arguments from url rule
        :type kwargs: dict
        :returns: response
        :rtype: werkzeug.wrappers.Response

        """
        context = self.get_context_data(**kwargs)
        return self.create_response(context)


class RedirectView(View):
    """Redirects to a given URL.

    The given URL may contain dictionary-style format fields which will be
    interpolated  against the keyword arguments captured from the URL rule
    using the :meth:`~str.format` method.

    An URL rule endpoint may be given instead, which will be passed to
    :meth:`~flask.url_for` along with any keyword arguments captured by the
    URL rule.

    When no URL can be found a :exc:`~werkzeug.exceptions.Gone` exception
    will be raised.

    .. code-block:: python

         class ShortView(RedirectView):

             permanent = True
             query_string = True
             endpoint = 'post-detail'

             def get_redirect_url(self, **kwargs):
                 post = Post.query.get_or_404(base62.decode(kwargs['code']))
                 kwargs['slug'] = post.slug
                 return super(ShortView, self).get_redirect_url(**kwargs)

            short_view = ShortView.as_view('short')

            app.add_url_rule('/s/<code>', view_func=short_view)

    The above example will redirect "short links" where the pk is base62
    encoded to the correct url.

    .. code-block:: python

        google_view = RedirectView.as_view('google', url='http://google.com/')

        app.add_url_rule('/google', view_func=google_view)

    It can also be used directly in a URL rule to avoid having to create
    additional classes for simple redirects.

    """
    url = None
    endpoint = None
    permanent = False
    query_string = False

    def get_redirect_url(self, **kwargs):
        """Retrieve URL to redirect to.

        When :attr:`url` is not None then it is returned after being
        interpolated with the keyword arguments using :meth:`~str.format`.

        When :attr:`url` is None and :attr:`endpoint` is not None
        then it is passed to :meth:`~flask.url_for` with the keyword arguments,
        and any query string is removed.

        The query string from the current request can be added to the new
        URL by setting :attr:`query_string` to ``True``.

        :param kwargs: keyword arguments
        :type kwargs: dict
        :returns: URL
        :rtype: str

        """
        if self.url is not None:
            url = self.url.format(**kwargs)
        elif self.endpoint is not None:
            try:
                url = url_for(self.endpoint, **kwargs)
            except BuildError:
                return None
            else:
                url = url_parse(url).replace(query='').to_url()
        else:
            return None

        query = request.environ.get('QUERY_STRING', '')

        if self.query_string and query:
            url = url_parse(url).replace(query=query).to_url()

        return url

    def dispatch_request(self, **kwargs):
        """Redirect the user to the result of.

        :meth:`~RedirectView.get_redirect_url`, when by default it will issue a
        302 temporary redirect, except when :attr:`permanent` is
        set to the ``True``, then a 301 permanent redirect will be used.

        When the redirect URL is None, a :exc:`~werkzeug.exceptions.Gone`
        exception will be raised.

        Any keyword arguments will be used to build the URL.

        :param kwargs: keyword arguments from url rule
        :type kwargs: dict
        :returns: response
        :rtype: werkzeug.wrappers.Response

        """

        url = self.get_redirect_url(**kwargs)

        if url is None:
            abort(410)

        if self.permanent:
            return redirect(url, code=301)

        return redirect(url)


class FormMixin(ContextMixin):
    """Provides facilities for creating and displaying forms."""

    data = {}
    form_class = None
    success_url = None
    prefix = ''

    def get_data(self):
        """Retrieve data to pass to the form.

        By default returns a copy of :attr:`data`.

        :returns: data
        :rtype: dict

        """

        return self.data.copy()

    def get_prefix(self):
        """Retrieve prefix to pass to the form.

        By default returns :attr:`prefix`.

        :returns: prefix
        :rtype: str

        """
        return self.prefix

    def get_formdata(self):
        """Retrieve prefix to pass to the form.

        By default returns a :class:`werkzeug.datastructures.CombinedMultiDict`
        containing :attr:`flask.request.form` and :attr:`flask.request.files`.

        :returns: form / file data
        :rtype: werkzeug.datastructures.CombinedMultiDict

        """
        return CombinedMultiDict([request.form, request.files])

    def get_form_kwargs(self):
        """Retrieve the keyword arguments required to instantiate the form.

        The ``data`` argument is set using :meth:`get_data` and the ``prefix``
        argument is set using :meth:`get_prefix`. When the request is a POST or
        PUT, then the ``formdata`` argument will be  set using
        :meth:`get_formdata`.

        :returns: keyword arguments
        :rtype: dict

        """
        kwargs = {'data': self.get_data(),
                  'prefix': self.get_prefix()}

        if request.method in ('POST', 'PUT'):
            kwargs['formdata'] = self.get_formdata()

        return kwargs

    def get_form_class(self):
        """Retrieve the form class to instantiate.

        By default returns :attr:`form_class`.

        :returns: form class
        :rtype: type
        :raises NotImplementedError: when :attr:`form_class` is not set

        """
        if self.form_class is None:
            error = ("{0} requires either a definition of 'form_class' or "
                     "an implementation of 'get_form_class()'")

            raise NotImplementedError(error.format(self.__class__.__name__))

        return self.form_class

    def get_form(self):
        """Create a :class:`~flask_wtf.Form` instance using
        :meth:`get_form_class` using :meth:`get_form_kwargs`.

        :returns: form
        :rtype: flask_wtf.Form

        """

        cls = self.get_form_class()

        return cls(**self.get_form_kwargs())

    def get_success_url(self):
        """Retrive the URL to redirect to when the form is successfully
        validated.

        By default returns :attr:`success_url`.

        :returns: URL
        :rtype: str
        :raises NotImplementedError: when :attr:`success_url` is not set

        """

        if self.success_url is None:
            error = ("{0} requires either a definition of 'success_url' or "
                     "an implementation of 'get_success_url()'")

            raise NotImplementedError(error.format(self.__class__.__name__))

        return self.success_url

    def form_valid(self, form):
        """Redirects to :meth:`get_success_url`.

        :param form: form instance
        :type form: flask_wtf.Form
        :returns: response
        :rtype: werkzeug.wrappers.Response

        """
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        """Creates a response using the return value of.

        :meth:`get_context_data()`.

        :param form: form instance
        :type form: flask_wtf.Form
        :returns: response
        :rtype: werkzeug.wrappers.Response

        """
        return self.create_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        """Extends the view context with a ``form`` variable containing the
        return value of :meth:`get_form`.

        :param kwargs: context
        :type kwargs: dict
        :returns: context
        :rtype: dict

        """
        kwargs.setdefault('form', self.get_form())

        return super(FormMixin, self).get_context_data(**kwargs)


class ProcessFormView(MethodView):
    """Provides basic HTTP GET and POST processing for forms.

    This class cannot be used directly and should be used with a
    suitable mixin.

    """

    def get(self, **kwargs):
        """Creates a response using the return value of.

        :meth:`get_context_data()`.

        :param kwargs: keyword arguments from url rule
        :type kwargs: dict
        :returns: response
        :rtype: werkzeug.wrappers.Response

        """
        return self.create_response(self.get_context_data())

    def post(self, **kwargs):
        """Constructs and validates a form.

        When the form is valid :meth:`form_valid` is called, when the form
        is invalid :meth:`form_invalid` is called.

        :param kwargs: keyword arguments from url rule
        :type kwargs: dict
        :returns: response
        :rtype: werkzeug.wrappers.Response

        """
        form = self.get_form()

        if form.validate():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def put(self, **kwargs):
        """Passes all keyword arguments to :meth:`post`.

        :param kwargs: keyword arguments from url rule
        :type kwargs: dict
        :returns: response
        :rtype: werkzeug.wrappers.Response

        """
        return self.post(**kwargs)


class BaseFormView(FormMixin, ProcessFormView):
    """View class to process handle forms without response creation."""


class FormView(TemplateResponseMixin, BaseFormView):
    """ View class to display a :class:`~flask_wtf.Form`. When invalid
    it shows the form with validation errors, when valid it redirects to a
    new URL.

    .. code-block:: python

        class ContactForm(Form):
            email = StringField('Name', [required(), email()])
            message = TextAreaField('Message', [required()])


        class ContactView(FormView):
            form_class = ContactForm
            success_url = '/thanks'
            template_name = 'contact.html'

            def form_valid(self, form):
                message = Message('Contact Form', body=form.message.data,
                                  recipients=['contact@example.com'],
                                  sender=form.email.data)

                mail.send(message)

                super(ContactView).form_valid(form)

    The above example will render the template ``contact.html`` with an
    instance of ``ContactForm`` in the context variable ``view``, when the user
    submits the form with valid data an email will be sent, and the user
    redirected to ``/thanks``, when the form is submitted with invalid data
    ``content.html`` will be rendered again, and the form will contain any
    error messages.
    """
