run:
	python manage.py runserver

migrate:
	python manage.py makemigrations
	python manage.py migrate

fixtures:

admin:
	python manage.py createsuperuser

start:
	make migrate
	make admin
	make run