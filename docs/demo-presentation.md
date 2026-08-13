# FoodBridge manual demonstration guide

## Prepare the demo

1. Apply the existing migrations, then load the safe demo dataset:

   ```bash
   python manage.py migrate
   python manage.py seed_demo
   python manage.py runserver
   ```

2. Open <http://127.0.0.1:8000/login/>. Every demo account uses the password printed by `seed_demo` (`FoodBridgeDemo123!`).
3. The seed command refreshes only users whose e-mail starts with `demo.` and their linked demonstration records. It never clears other users or records. Run it again whenever a walkthrough step changes a demo record.
4. Optional payment and payout-profile screen: use a local-only encryption key and enable payment pages for both commands. This only exposes the already-completed simulated record; do not click a payment or payout action.

   ```bash
   PAYMENT_ENCRYPTION_KEY=local-demo-key FOODBRIDGE_PAYMENTS_ENABLED=true python manage.py seed_demo
   PAYMENT_ENCRYPTION_KEY=local-demo-key FOODBRIDGE_PAYMENTS_ENABLED=true python manage.py runserver
   ```

## Accounts

| Role | E-mail | What it demonstrates |
| --- | --- | --- |
| Donor | `demo.donor@foodbridge.local` | Profile, food listings, statuses, delivery evidence |
| Volunteer | `demo.volunteer@foodbridge.local` | Nearby available pickup, live location, in-transit work, delivery history |
| Approved NGO | `demo.ngo@foodbridge.local` | Available food, safety review, takeover, receipt, delivery confirmation |
| Pending NGO | `demo.pending-ngo@foodbridge.local` | NGO approval-pending dashboard |

## Suggested presentation order

1. **Public entry points.** Visit the home page, then open registration. Show that the Donor, Volunteer, and NGO entry points select their respective registration forms. Return to login rather than creating another account.
2. **Donor journey.** Log in as the donor. Open **Dashboard**, **My donations**, and `[DEMO] Available food listing` to show the information captured for a food listing: safety photos, food details, pickup window, and location. Open `[DEMO] Completed volunteer delivery` to show the final status and delivery evidence.
3. **NGO approval state.** Log out, sign in as the pending NGO, and open its dashboard. Point out that the account cannot operate on listings until approval. Log out.
4. **Food safety review.** Sign in as the approved NGO and open <http://127.0.0.1:8000/donations/food-review/>. Show the pending human-review listing and the separate rejected listing in the donor’s list. You may approve or reject the pending review to show the action; rerun `seed_demo` afterwards to restore it.
5. **NGO food management.** Open <http://127.0.0.1:8000/donations/>. Explain the available listings, including `[DEMO] NGO rejection reopened listing`. Open `[DEMO] NGO takeover awaiting receipt` from **Managed donations** to show the receipt-upload and return-to-queue options. Do not submit an external payment action.
6. **Volunteer collection.** Log in as the volunteer. On **Dashboard**, show the available-pickup count and the recent location. Open **Available Pickups** to show `[DEMO] NGO accepted - ready for volunteer`; it is ready to claim because an NGO has accepted it. Open **Assigned Pickups** and `[DEMO] Collected - live location` to explain collection, delivery destination, and live location sharing.
7. **Completed delivery and payment state.** Open **Pickup History** and `[DEMO] Completed volunteer delivery`. It contains delivery proof. If the optional local-only payment setup above is running, log in as the approved NGO and open the `Payment detail` URL printed by `seed_demo`; it shows the completed simulated payout. Log in as the volunteer to open **Payout details** and show the masked demo UPI destination. These are presentation records only and do not represent Razorpay transactions.
8. **NGO confirmation.** Return to the approved NGO and open the completed-delivery listing. Explain that an NGO confirms delivery before a volunteer payment is progressed. The seeded completed record represents the end state; no real checkout or payout is performed.

## Reset and safety

- Rerun `python manage.py seed_demo` to reset only the demo accounts, their donations, pickups, payment records, and demo images.
- The command does not call Gemini, Razorpay, map, geocoding, or any other external service.
- Do not enter real payout details or press a payment/payout action during this demonstration.
