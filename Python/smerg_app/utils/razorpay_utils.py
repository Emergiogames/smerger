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
    client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
    try:
        order = client.order.create({
            "amount": 10000,
            "currency": "INR",
            # "receipt": "receipt#1",
        })
        return order
    except Exception as e:
        print(f"An error occurred: {e}")
        return None