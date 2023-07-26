runserver:
	python manage.py runserver

runbot:
	python manage.py bot

migrate:
	python manage.py makemigrations
	python manage.py migrate

fixtures:
	python manage.py loaddata OrderStatus.json

admin:
	python manage.py createsuperuser

start:
	make migrate
	make admin
	make fixtures
	make runserver