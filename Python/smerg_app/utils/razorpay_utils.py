#################################  R A Z O R P A Y  P A Y M E N T  V E R I F I C A T I O N  #################################
import asyncio
import razorpay
from django.conf import settings

# async def verify_payment(transaction_key):
#     client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))

#     try:
#         payment_details = await asyncio.to_thread(client.payment.fetch, transaction_key)

#         if payment_details['status'] == 'captured':
#             return True, payment_details
#         else:
#             return False, payment_details

#     except Exception as e:
#         return False, str(e)

def verify_payment(transaction_key, amount):
    print(f"Amount: {amount}")
    print(f"Transaction Key: {transaction_key}")
    client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
    amount_in_paise = int(int(amount) * 100)
    print(amount_in_paise)
    payment_details = client.payment.capture(transaction_key,{
        "amount" : 100,
        "currency" : "INR"
    })
    print(payment_details)
    if payment_details['status'] == 'captured':
        return True, payment_details
    else:
        return False, payment_details

def create_order(amount):
    client = razorpay.Client(auth=(settings.RAZORPAY_API_KEY, settings.RAZORPAY_API_SECRET))
    try:
        amount_in_paise = int(int(amount) * 100)
        order = client.order.create({
            "amount": amount_in_paise,
            "currency": "INR",
            # "receipt": "receipt#1",
        })
        order['key'] = settings.RAZORPAY_API_KEY
        return order
    except Exception as e:
        print(f"An error occurred: {e}")
        return None