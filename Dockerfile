FROM python
COPY . /crawler
WORKDIR /crawler
RUN pip install -r requirements.txt
CMD bash ./helpers/start_app.sh
