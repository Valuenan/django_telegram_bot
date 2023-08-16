runserver:
	python manage.py runserver

runbot:
	python manage.py bot

runbot_nohup:
	nohup runbot &

migrate:
	python manage.py makemigrations
	python manage.py migrate

fixtures:
	python manage.py loaddata DefaultData.json

admin:
	python manage.py createsuperuser

start:
	make migrate
	make admin
	make fixtures
	make runserver

dumpdata:
	python -Xutf8 manage.py dumpdata > data.json