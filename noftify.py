import smtplib, email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.header import Header

class EmailSender:
    def __init__(self, rcv_addr, send_addr, smtp_addr, auth_code):
        # self.smtp = 'smtp.' + addr.split("@")[1]
        self.smtp = smtp_addr
        self.send_addr = send_addr
        self.rcv_addr = rcv_addr
        self.auth_code  = auth_code

    def send(self, subject, content):
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"]    = self.send_addr
        msg["To"]      = self.rcv_addr
        text = MIMEText(content, "html", "utf-8")
        msg.attach(text)
        smtp = smtplib.SMTP()
        smtp.connect(self.smtp)
        smtp.login(self.send_addr, self.auth_code)
        smtp.sendmail(self.send_addr, self.rcv_addr, msg.as_string())
        smtp.quit()
