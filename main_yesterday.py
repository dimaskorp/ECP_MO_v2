from requests.exceptions import HTTPError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from requests import Session
import datetime
import smtplib
import subprocess
import time

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36'}

TIMEOUT = 0.1

date1 = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%d.%m.%Y')  # Вчерашняя дата 1
date2 = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%d.%m.%Y')  # Вчерашняя дата 2

url = "https://ecp18.is-mis.ru/"
url_autoriz = "https://ecp18.is-mis.ru/?c=main&m=index&method=Logon&login=ZainutdinovD"
url_object_ID = "https://ecp18.is-mis.ru/?c=EMD&m=loadEMDSignBundleWindow"
url_sing_data = "https://ecp18.is-mis.ru/?c=EMD&m=getEMDVersionSignData"
url_signatures = "https://ecp18.is-mis.ru/?c=EMD&m=saveEMDSignatures"
url_certificate = "https://ecp18.is-mis.ru/?c=EMD&m=loadEMDCertificateEditWindow"

param_autoriz = {
    "login": "ZainutdinovD",
    "psw": "*******",
    "swUserRegion": "",
    "swUserDBType": ""
}

param_object_ID = {
    "EMDLpu_id": "180101000000022",
    "LpuBuilding_id": "null",
    "EMDRegistry_EMDDate_period": str(date1) + " — " + str(date2),
    "EMDVersion_RegistrationDate_period": "",
    "EMDRegistry_Num": "",
    "Person_FIO": "",
    "EMDDocumentType_Code": "null",
    "EMDVersionStatus": "",
    "isLpuSignNeeded": "on",
    "hidedeletedoc": "1",
    "limit": "10000",
    "isMOSign": "true",
    "start": "0"
}

param_sing_data = {
    "EMDRegistry_ObjectName": "",
    "EMDRegistry_ObjectID": "",
    "MedStaffFact_id": "",
    "isMOSign": "true",
    "EMDCertificate_id": "8851",
    "EMDVersion_VersionNum": "1"
}

param_signatures = {
    "EMDRegistry_ObjectName": "",  # Наименование объекта
    "EMDRegistry_ObjectID": "",  # Идентификатор объекта
    "EMDVersion_id": "",  # Идентификатор версии в регистре
    "Signatures_Hash": "",  # Хэш
    "Signatures_SignedData": "",  # Подпись
    "EMDCertificate_id": "8851",  # Сертификат
    "signType": "cryptopro",  # Тип подписи
    "isMOSign": "true",  # Наименование объекта
    "LpuSection_id": "",
    "MedService_id": ""
}


def send_ecp_mo():
    try:
        with Session() as session_rt_mis:
            auth = session_rt_mis.post(url_autoriz, data=param_autoriz)  # сеанс будет закрыт сразу же после выхода из блока with.
            if auth.status_code == 200:
                list_object_ID = session_rt_mis.post(url_object_ID, data=param_object_ID).json()
                print(f"Всего документов: {len(list(list_object_ID))}")
                signed_documents = 0
                for x, i in enumerate(list_object_ID):
                    if i['IsSigned'] == '2':  # проверка стоит ли подпись врача
                        object_ID = i['EMDRegistry_ObjectID']
                        version_id = i['EMDVersion_id']
                        object_name = i['EMDRegistry_ObjectName']
                        param_signatures['EMDVersion_id'] = version_id
                        param_sing_data['EMDRegistry_ObjectID'] = object_ID
                        param_signatures['EMDRegistry_ObjectID'] = object_ID
                        param_sing_data['EMDRegistry_ObjectName'] = object_name
                        param_signatures['EMDRegistry_ObjectName'] = object_name
                        list_sing_data = session_rt_mis.post(url_sing_data, data=param_sing_data).json()
                        if list_sing_data['success']:
                            signatures_hash = list_sing_data['toSign'][0]['hashBase64']
                            version_id = list_sing_data['toSign'][0]['EMDVersion_id']
                            param_signatures['Signatures_Hash'] = signatures_hash
                            param_signatures['EMDVersion_id'] = version_id
                            var = subprocess.run(f"docker exec cryptopro /scripts/sign {signatures_hash}", stdout=subprocess.PIPE).stdout.decode('utf-8')
                            if var:
                                param_signatures["Signatures_SignedData"] = var
                            else:
                                send_mail(str(f"Внимание!!! Нет связи с Docker"))
                                break
                            # param_signatures["Signatures_SignedData"] = signed_data.signed(signatures_hash)
                            message = session_rt_mis.post(url_signatures, data=param_signatures).json()
                            if message['success']:
                                print(f"Документ №{x + 1} подписан")
                                signed_documents += 1
                            else:
                                print(message['Error_Msg'])
                            time.sleep(0.2)
                        else:
                            print(list_sing_data['Error_Msg'])
                            continue
                    elif i['IsSigned'] == '1':
                        print(f"Документ №{x + 1} номер: {str(i['Document_Num'])} не подписан надлижащим образом")
                        time.sleep(0.2)
                        continue
                    elif i['IsSigned'] == '-1':
                        print(f"Документ №{x + 1} номер: {str(i['Document_Num'])} удален и не может быть подписан")
                        time.sleep(0.2)
                        continue
                print(str(f"Документов подписано: {str(signed_documents)}"))
                send_mail(str(f"Всего документов за прошедший месяц: {len(list(list_object_ID))}\n"
                              f"из них подписано: {str(signed_documents)}"))
            else:
                print(str(auth.status_code))
                send_mail(str(auth.status_code))
    except HTTPError as http_err:
        print(f'HTTP error occurred:\n {http_err}')
        send_mail(str(http_err))
        time.sleep(900)
    except Exception as err:
        print(f'Other error occurred:\n {err}')
        send_mail(str(err))
        time.sleep(900)


def send_mail(body):
    fromaddr = 'prog-rkib@mail.ru'
    toaddr = 'prog-rkib@mail.ru'
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "РТ МИС "
    msg.attach(MIMEText(body, 'plain'))
    server = smtplib.SMTP('smtp.mail.ru', 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(fromaddr, '********************')
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()


if __name__ == '__main__':
    send_ecp_mo()
