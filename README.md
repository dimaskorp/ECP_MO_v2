# КриптоПро 5.0 в докер контейнере c расширением pycades
Проект переделан для возможности автоматического подписания электронных медицинских документов на портале РТ МИС (доступен только из защищенной сети Минздрава УР)

[Инструкция по установке и сборке расширения для языка Python](https://docs.cryptopro.ru/cades/pycades/pycades-build)

Содержимое контейнера:

* python3.9.10 с установленным расширением `pycades` (`CPStore`, `CPSigner`, `CPSignedData`)
* инструменты КриптоПро: `certmgr`, `cpverify`, `cryptcp`, `csptest`, `csptestf`, `der2xer`, `inittst`, `wipefile`, `cpconfig`
* вспомогательные скрипты командой строки


# Структура проекта

```
├── certificates  - Корневые сертификаты и сертификаты пользователей
├── dist          - пакеты КриптоПро (необходимо скачать с официального сайта)
├── Dockerfile    - файл сборки образа
├── README.md     - этот файл
└── scripts       - вспомогательные скрипты командой строки
````

# Создание образа из исходного кода

Скачать с официального сайта в `dist/` (необходимо быть залогиненым в системе):

* [КриптоПро CSP 5.0 для Linux (x64, deb)](https://www.cryptopro.ru/products/csp/downloads) => `dist/linux-amd64_deb.tgz`
* КриптоПро ЭЦП SDK [версия 2.0 для пользователей](https://cryptopro.ru/products/cades/downloads) => `dist/cades-linux-amd64.tar.gz` - Linux версию
* [Архив с исходниками](https://cryptopro.ru/sites/default/files/products/cades/pycades/pycades.zip) => `dist/pycades.zip`

Запустить:

```shell
docker build --tag cryptopro_5 .
```

## Возможные проблемы

В `Dockerfile` содержатся названия пакетов, например `lsb-cprocsp-devel_5.0.12000-6_all.deb`, которые могут заменить новой версией. Следует поправить названия пакетов в `Dockerfile`.

# Запуск контейнера

Запустим контейнер под именем `cryptopro`, к которому будем обращаться в примерах:

```shell
docker run -it -p 8095:80 --name cryptopro cryptopro_5
```

# Работа с контейнером через интерфейс командной строки<a name="cli"></a>

## Лицензия

Установка серийного номера:

```shell
docker exec -i cryptopro cpconfig -license -set <серийный_номер>
```

Просмотр:

```shell
docker exec -i cryptopro cpconfig -license -view
```

![license](./assets/license.gif)


## Установка корневых сертификатов

Для установки корневых сертификатов нужно на `stdin` скрипта `/scripts/root` передать файл с сертификатами. Если в файле несколько сертификатов, все они будут установлены.


### Без скачивания на диск

# Корневые сертификаты Федерального казначейства

Сетификаты нужно скачать с сайта https://roskazna.gov.ru/gis/udostoveryayushhij-centr/kornevye-sertifikaty/
и поместить их в архив <name>.p7b в папку certificates

Добавление корневых сертификатов (под root) из файла <name>.p7b:

```shell
docker exec -i cryptopro certmgr -inst -all -store uroot -file /certificates/certs.p7b
```


## Добавление реального сертификата с привязкой к закрытому ключу и возможностью подписывать документы

Скопировать приватный ключ в хранилище (контейнер), где <username> - имя пользователя linux:
```shell
docker exec -i cryptopro cp -R /certificates/ecp/mo.000 /var/opt/cprocsp/keys/root
```
Поставить «минимальные» права:
```shell
docker exec -i cryptopro chmod 766 /var/opt/cprocsp/keys/root/mo.000/*
```
Узнать реальное название контейнера:
```shell
docker exec -i cryptopro csptest -keyset -enum_cont -verifycontext -fqcn   # \\.\HDIMAGE\1021801592230 327155959
```
Ассоциировать сертификат с контейнером, сертификат попадет в пользовательское хранилище My:
```shell
docker exec -i cryptopro certmgr -inst -file /certificates/ecp/mo2023.cer -cont '\\.\HDIMAGE\mo'
```
Если следующая ошибка, нужно узнать реальное название контейнера (см. выше):

Failed to open container \\.\HDIMAGE\<container>
[ErrorCode: 0x00000002]
Установить сертификат УЦ из-под пользователя root командой:
```shell
docker exec -i cryptopro certmgr -inst -store root -file /certificates/ecp/mo2023.cer
```
Проверка успешности установки закрытого ключа
```shell
docker exec -i cryptopro certmgr --list
```
Удаление пин кода из контейнера (выполнять лучше из BASH 'csptest -passwd -cont '\\.\HDIMAGE\Diachenk.000' -pass 12345678 -change "" ') (docker exec -it cryptopro bash )
```shell
docker exec -i cryptopro csptest -passwd -cont '\\.\HDIMAGE\mo' -pass 12345678 -change "" 
```

## Просмотр установленных сертификатов

Сертификаты пользователя:

```shell
docker exec -i cryptopro certmgr -list
```

![show-certs](./assets/show-certs.gif)

Корневые сертификаты:

```shell
docker exec -i cryptopro certmgr -list -store root
```

## Подписание документа

hash строка передается на `sign` файл в контейнере, в качестве команды - последовательность действий, и на `stdout` получим подписанную hash строку:
Команта прописана в файле main.py
```shell
var = subprocess.run(f"docker exec cryptopro /scripts/sign {signatures_hash}", stdout=subprocess.PIPE).stdout.decode('utf-8')
```



https://pushorigin.ru/cryptopro/cryptcp