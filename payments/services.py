import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_stripe_product(name):
    product = stripe.Product.create(name=name)
    return product


def create_stripe_price(product_id, amount):
    price = stripe.Price.create(
        currency="rub", unit_amount=amount * 100, product=product_id
    )
    return price


def create_stripe_session(price_id):
    session = stripe.checkout.Session.create(
        success_url=settings.STRIPE_SUCCESS_URL,
        cancel_url=settings.STRIPE_CANCEL_URL,
        line_items=[{"price": price_id, "quantity": 1}],
        mode="payment",
    )
    return session
