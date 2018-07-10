#!/usr/bin/env python3
import os

from flask import jsonify, Flask


app = Flask(__name__)


@app.route('/api/info')
def api():
    return jsonify({
        'appName': os.environ.get('PROJECT_DESCRIPTION', 'Chops Example Web Application'),
    })


def main():
    import os
    app.run(host='0.0.0.0', port=int(os.environ.get('API_SERVER_PORT', 5000)))


if __name__ == '__main__':
    main()
