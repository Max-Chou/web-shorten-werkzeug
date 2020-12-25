import os
import redis
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from whitenoise import WhiteNoise
from werkzeug.utils import redirect
from jinja2 import Environment, FileSystemLoader


from utils import is_valid_url, base62_encoder

# WSGI App
class Shortly(object):
    def __init__(self, config, templates_dir="templates", static_dir="static"):
        self.redis = redis.Redis(config['redis_host'], config['redis_port'])
        self.whitenoise = WhiteNoise(self.wsgi_app, root=static_dir)
        self.templates_env = Environment(
            loader=FileSystemLoader(os.path.abspath(templates_dir))
        )
        # routing
        self.url_map = Map([
            Rule('/add', endpoint="add_url"),
            Rule('/<short_id>', endpoint="redirect_url"),
            Rule('/<short_id>+', endpoint="url_info")
        ])

    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, endpoint)(request, **values)
        except HTTPException as e:
            return e

    def render_template(self, template_name, **context):
        tpl = self.templates_env.get_template(template_name)
        return Response(tpl.render(context), mimetype='text/html')

    def add_url(self, request):
        error = None
        url = None
        if request.method == 'POST':
            url = request.form['url']
            if not is_valid_url(url):
                error = 'Please enter a valid URL'
            else:
                short_id = self.insert_url(url)
                return redirect(f'/{short_id}+')

        return self.render_template('new_url.html', error=error, url=url)
    
    def insert_url(self, url):
        short_id = self.redis.get('reverse-url:'+ url)
        if short_id:
            return short_id
        url_num = self.redis.incr('last-url-id')
        short_id = base62_encoder(url_num)
        self.redis.set('url-target:' + short_id, url)
        self.redis.set('reverse-url:' + url, short_id)
        return short_id

    def redirect_url(self, request, short_id):
        link_target = self.redis.get('url-target:'+ short_id)
        if not link_target:
            raise NotFound
        self.redis.incr('click-count:'+ short_id)
        return redirect(link_target)
    
    def url_info(self, request, short_id):
        link_target = self.redis.get('url-target:' + short_id)
        if not link_target:
            raise NotFound
        click_count = int(self.redis.get('click-count:' + short_id) or 0)
        return self.render_template('short_link.html',
            link_target=link_target,
            short_id=short_id,
            click_count=click_count,
        )

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)
    
    def __call__(self, environ, start_response):
        path_info = environ["PATH_INFO"]
        if path_info.startswith("/static"):
            environ["PATH_INFO"] = path_info[len("/static"):]
            return self.whitenoise(environ, start_response)
        return self.wsgi_app(environ, start_response)


if __name__ == '__main__':
    from werkzeug.serving import run_simple
    config = {
        'redis_host': 'localhost',
        'redis_port': 6379
    }
    app = Shortly(config)
    run_simple('localhost', 5000, app, use_debugger=True, use_reloader=True)
