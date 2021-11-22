import smtplib, email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.header import Header

class EmailSender:
    def __init__(self, addr, pwd, smtp_addr):
        # self.smtp = 'smtp.' + addr.split("@")[1]
        self.smtp = smtp_addr
        self.addr = addr
        self.pwd  = pwd

    def send(self, subject, content):
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"]    = self.addr
        msg["To"]      = self.addr
        text = MIMEText(content, "html", "utf-8")
        msg.attach(text)
        smtp = smtplib.SMTP()
        smtp.connect(self.smtp)
        smtp.login(self.addr, self.pwd)
        smtp.sendmail(self.addr, self.addr, msg.as_string())
        smtp.quit()
