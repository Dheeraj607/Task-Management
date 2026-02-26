# Task Management System

## Create Virtual environment and activate it
python -m venv venv
venv/scripts/activate

## Clone git repository
git clone https://github.com/Dheeraj607/Task-Management.git

## Install requirements
pip install -r requirements.txt

## Apply Migrations
python manage.py migrate

## Create super admin
python manage.py createsuperuser

## Run Server
python manage.py runserver

## server running on http://127.0.0.1:8000/ (click on the link)


## APIs
- [POST] http://127.0.0.1:8000/api/login/ - user login
- [POST] http://127.0.0.1:8000/api/token/refresh/ - refresh access token
- [GET] http://127.0.0.1:8000/api/my-tasks/ - tasks of current user
- [PUT] http://127.0.0.1:8000/api/tasks/:id/update/ - update task status
- [GET] http://127.0.0.1:8000/api/tasks/completed/ - task report

Postman collection attached with mail and git repository