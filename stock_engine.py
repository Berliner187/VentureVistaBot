from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, render_template

from stock_manager import work_of_the_stock_exchange, COMPANY_PRICES

app = Flask(__name__)
scheduler = BackgroundScheduler()


__version__ = '0.0.0.1'


if __name__ == '__main__':
    global COMPANY_PRICES
    scheduler.add_job(work_of_the_stock_exchange, 'interval', seconds=3)
    scheduler.start()

    @app.route('/data', methods=['GET'])
    def get_data():
        return jsonify(COMPANY_PRICES)

    @app.route('/')
    def main_page():
        return render_template('index.html', data=COMPANY_PRICES)

    app.run()
