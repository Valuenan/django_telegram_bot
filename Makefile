runserver:
	python manage.py runserver

runcelery:
	celery -A django_telegram_bot worker -l info

runbot:
	python manage.py bot

runbot_nohup:
	nohup make runbot &

runcheck:
	python manage.py services

runcheck_nohup:
	nohup make runcheck &

runservices:
	make runbot_nohup
	make runcheck_nohup

migrate:
	python manage.py makemigrations
	python manage.py migrate

migrate_docker:
	docker-compose run web python manage.py migrate

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