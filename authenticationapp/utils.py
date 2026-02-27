from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import threading

class SendEmailThread(threading.Thread):
    # This prepares the thread to run run() method in the background
    def __init__(self,email):
        self.email=email
        threading.Thread.__init__(self)
    def run(self):
        self.email.send()

def send_activation_email_threaded(recipient_email, activation_url):
    subject='Activate your account on ' + settings.SITE_NAME
    from_email=settings.DEFAULT_FROM_EMAIL
    to_email=[recipient_email]

    # load the html template
    html_content=render_to_string('email/activation_email.html',{'activation_url':activation_url}) # takes your HTML template (activation_email.html) and fills in the activation link
    text_content=strip_tags(html_content) # makes a plain text version in case some email clients don’t show HTML
    email=EmailMultiAlternatives(subject,text_content,from_email,to_email) # allows plain text + HTML email in one messag
    email.attach_alternative(html_content,'text/html') # attaches the HTML version
    SendEmailThread(email).start()

def send_password_reset_email_threaded(recipient_email, reset_url):
    subject='Reset your password on ' + settings.SITE_NAME
    from_email=settings.DEFAULT_FROM_EMAIL
    to_email=[recipient_email]

    # load the html template
    html_content=render_to_string('email/password_reset_email.html',{'reset_url':reset_url}) # takes your HTML template (activation_email.html) and fills in the activation link
    text_content=strip_tags(html_content) # makes a plain text version in case some email clients don’t show HTML
    email=EmailMultiAlternatives(subject,text_content,from_email,to_email) # allows plain text + HTML email in one messag
    email.attach_alternative(html_content,'text/html') # attaches the HTML version
    SendEmailThread(email).start()
    # SendEmailThread(email) -> creates a new thread object
    # .start()
    # tells Python:
    # “Hey, run this thread in parallel to the main program.”
    # Immediately returns control to the main program.
    # Main program does NOT wait for email to finish sending.

