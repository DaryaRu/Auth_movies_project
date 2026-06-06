###### Подготовка сервиса к запуску
Создать приватный и публичный ключи
```
openssl genrsa -out private.pem 2048
openssl rsa -in private.pem -pubout -out public.pem
```
Создание суперпользователя
```
python src/commands/create_superuser.py 
```