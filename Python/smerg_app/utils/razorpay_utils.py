#################################  R A Z O R P A Y  P A Y M E N T  V E R I F I C A T I O N  #################################
import asyncio
import razorpay
from django.conf import settings

async def verify_payment(transaction_key):
    client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

    try:
        payment_details = await asyncio.to_thread(client.payment.fetch, transaction_key)

        if payment_details['status'] == 'captured':
            return True, payment_details
        else:
            return False, payment_details

    except Exception as e:
        return False, str(e)

def create_order(amount):
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
        order = client.order.create({
            "amount": 10000,
            "currency": "INR",
            # "receipt": "receipt#1",
        })
        return order
    except razorpay.errors.AuthenticationError as e:
        print("Authentication Failed. Please check your API key and secret.")
        return None
    except razorpay.errors.BadRequestError as e:
        print("Bad Request. Please check the request payload.")
        return None
    except Exception as e:
        print("An unexpected error occurred:", e)
        return None