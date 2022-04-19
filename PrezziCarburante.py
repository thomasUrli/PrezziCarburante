import requests
from bs4 import BeautifulSoup
from datetime import date
from os import environ

import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

PREZZI_BENZINA_FUEL_STATIONS = {"Nome distributore": ["URL", "Nome_prezzo"]}

CONAD_FUEL_ORDER = ["DIESEL", "BENZINA"]
CITTA_FIERA_URL = "https://www.conad.it/ricerca-negozi/negozio.050404.html"

SENDER_EMAIL = ""
SMTP_SERVER = ""
SMTP_PORT = 587
RECEIVERS_EMAIL = [""]


def get_prezzi_benzina_fuel_info(session, fuel_station_url, price_description, final_strings):
    """
        Retrieves fuel info from a Prezzi Benzina fuel station url. MODIFY final_strings

        :param session: Session object
        :param fuel_station_url: Url of the fuel station on the Prezzi Benzina website
        :param price_description: Name associated to price on the Prezzi Benzina fuel station
        :param final_strings: Array containing the price details for petrol and diesel as strings
    """

    page = session.get(fuel_station_url)
    soup = BeautifulSoup(page.content, "html.parser")

    benzina = soup.find("div", class_="st_reports_fuel benzina_label").find_next("div", class_="st_reports_service", string=price_description)
    diesel = soup.find("div", class_="st_reports_fuel diesel_label").find_next("div", class_="st_reports_service", string=price_description)

    final_strings.append("DIESEL: " + diesel.find_next("div", class_="st_reports_price").text.replace('.', ',') +
                         "\nUltimo aggiornamento: " + diesel.find_previous("div", class_="st_reports_data").text[:-6] + "\n")
    final_strings.append("BENZINA: " + benzina.find_next("div", class_="st_reports_price").text.replace('.', ',') +
                         "\nUltimo aggiornamento: " + benzina.find_previous("div", class_="st_reports_data").text[:-6] + "\n")


def get_conad_fuel_info(session, final_strings):
    """
        Retrieves fuel info from a Conad fuel station url. MODIFY final_strings

        :param session: Session object
        :param final_strings: Array containing the price details for petrol and diesel as strings
    """

    page = session.get(CITTA_FIERA_URL)
    soup = BeautifulSoup(page.content, "html.parser")

    prices = soup.find_all("div", class_="box box-price-simple")

    for fuel in CONAD_FUEL_ORDER:
        final_strings.append(fuel + ": " + prices.pop().p.text +
                             "\nUltimo aggiornamento: " + str(date.today().strftime("%d/%m/%Y")) + " \n")


def email_message_creator(prezzi_benzina_final_strings, conad_final_strings):
    """
        Combines the final strings to create the email text.

        :param prezzi_benzina_final_strings: Array containing the fuel info for Prezzi Benzina fuel stations
        :param conad_final_strings: Array containing the fuel info for Conad fuel station
        :return: Plain and html text of the email
    """

    final_plain_text = "DISTRIBUTORE CITTÀ FIERA \n" + conad_final_strings[0] + " \n" + conad_final_strings[1] + "\n"
    final_html_text = "<h2>DISTRIBUTORE CITTÀ FIERA </h2><p style=\"font-size:15px\">" + conad_final_strings[0].replace("\n", "<br>") + "<br>" + conad_final_strings[1].replace("\n", "<br>") + "<br></p>"

    for i, st_name in enumerate(PREZZI_BENZINA_FUEL_STATIONS):
        final_plain_text += st_name + " \n" + prezzi_benzina_final_strings[i*2] + " \n" + prezzi_benzina_final_strings[i*2 + 1] + "\n"
        final_html_text += "<h2>" + st_name + "</h2><p style=\"font-size:15px\">" + prezzi_benzina_final_strings[i*2].replace("\n", "<br>") + "<br>" + prezzi_benzina_final_strings[i*2+1].replace("\n", "<br>") + "<br></p>"

    return final_plain_text, final_html_text


def send_email(plain_text, html_text, receivers):
    """
        Creates and sends an email.

        :param plain_text: Plain text of the email
        :param html_text: Html text of the email
        :param receivers: Array containing all the receivers email
    """

    password = environ["PW_CARBURANTE"]

    message = MIMEMultipart("alternative")
    message["Subject"] = "Prezzi Carburante del " + date.today().strftime("%d/%m/%Y")
    message["From"] = "Prezzi Carburante <" + SENDER_EMAIL + ">"
    message["To"] = ",".join(receivers)

    # Create the plain-text and HTML version of your message
    html = """\
    <html><body>{fuel_info}</body></html>
    """
    html = html.format(fuel_info = html_text)

    # Turn these into plain/html MIMEText objects
    part1 = MIMEText(plain_text, "plain")
    part2 = MIMEText(html, "html")

    # Add HTML/plain-text parts to MIMEMultipart message
    # The email client will try to render the last part first
    message.attach(part1)
    message.attach(part2)

    # Create secure connection with server and send email
    smtp_server = smtplib.SMTP(SMTP_SERVER, port=SMTP_PORT)

    context = ssl.create_default_context()

    if smtp_server.starttls(context=context)[0] != 220:
        return False  # cancel if connection is not encrypted

    smtp_server.login(SENDER_EMAIL, password)
    smtp_server.sendmail(SENDER_EMAIL, receivers, message.as_string())
    smtp_server.quit()


if __name__ == "__main__":
    session = requests.Session()

    prezzi_benzina_final_strings = []
    for fuel_station in PREZZI_BENZINA_FUEL_STATIONS.values():
        get_prezzi_benzina_fuel_info(session, fuel_station[0], fuel_station[1], prezzi_benzina_final_strings)

    conad_final_strings = []
    get_conad_fuel_info(session, conad_final_strings)

    plain_message, html_message = email_message_creator(prezzi_benzina_final_strings, conad_final_strings)

    send_email(plain_message, html_message, RECEIVERS_EMAIL)
