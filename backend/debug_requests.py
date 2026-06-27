import traceback
from app import create_app

app = create_app('development')

with app.app_context():
    client = app.test_client()

    urls = ['/api/departments', '/api/analytics/stream']
    for url in urls:
        try:
            print('REQUEST', url)
            resp = client.get(url)
            print('STATUS', resp.status_code)
            print('HEADERS', resp.headers)
            print('BODY', resp.get_data(as_text=True)[:1000])
        except Exception as e:
            print('EXCEPTION', e)
            traceback.print_exc()
