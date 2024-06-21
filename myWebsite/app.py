from website import create_app


class FlaskApp:
    def __init__(self):
        self.app = create_app()

    def run(self):
        self.app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    app = FlaskApp()
    app.run()
    