from datetime import datetime, timedelta, timezone
import braintree


def transaction_to_dict(txn):
    """Extracts useful fields from a Braintree Transaction object into a flat dict."""
    return {
        "id": txn.id,
        "status": txn.status,
        "amount": float(txn.amount) if txn.amount is not None else None,
        "created_at": txn.created_at.isoformat() if txn.created_at else None,
        "updated_at": txn.updated_at.isoformat() if txn.updated_at else None,
        "order_id": txn.order_id,
        "customer_id": txn.customer_details.id if txn.customer_details else None,
        "customer_email": txn.customer_details.email if txn.customer_details else None,
        "merchant_account_id": txn.merchant_account_id,
        "payment_instrument_type": txn.payment_instrument_type,
        # Add more fields as needed...
    }
    
def fetch_transactions_last_n_days(n: int, merchant_id,public_key,private_key):
    """
    Fetches Braintree transactions from the last n days.
    
    Parameters:
        n (int): Number of days to look back.
    
    Returns:
        List[braintree.Transaction]: A list of matching transaction objects.
    """

    gateway=braintree.BraintreeGateway(
        braintree.Configuration(
            environment=braintree.Environment.Production,
            merchant_id=merchant_id,
            public_key=public_key,
            private_key=private_key
            )
        )

    # Calculate the cutoff datetime (UTC)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=n)

    collection = gateway.transaction.search(braintree.TransactionSearch.created_at.between(cutoff,now))
    results = []

    for txn in collection.items:
      results.append(transaction_to_dict(txn))

    return results

def sync_transactions_last_n_days(supabase, n: int, merchant_id,public_key,private_key):
    transactions=fetch_transactions_last_n_days(n, merchant_id,public_key,private_key)
    print(f"Got {len(transactions)=} transactions from {n} days")
    for t in transactions:
        supabase.upsert_braintree(t)
    return transactions


