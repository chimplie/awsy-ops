#!/usr/bin/env python3
from flask import jsonify, Flask


app = Flask(__name__)


@app.route('/api/info')
def api():
    return jsonify({
        'appName': 'Chops Example Web Application',
    })


def main():
    import os
    app.run(host='0.0.0.0', port=int(os.environ.get('API_SERVER_PORT', 5000)))


if __name__ == '__main__':
    main()
