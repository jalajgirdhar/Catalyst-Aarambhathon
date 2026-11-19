# StockWise: 3-minute demo script

**Setup before you go on stage (do this twice at home):**
- Open the app, sidebar: Demo (synthetic) > Ethnic wear boutique > 1 store > "Before Diwali (like Meera's case)".
- Open the live link a few minutes early so it is awake. Keep `streamlit run app.py` ready on a laptop as backup.
- Take screenshots of every screen below as a last-resort backup.
- **Numbers on your screen may differ slightly from the ones below** (your computer uses a different forecasting library than the one I tested with). Rehearse once, then write the numbers you actually see next to each step.

---

## 0:00 - 0:20  The problem (slide, not the app)
> "Meera runs a small ethnic-wear shop. Diwali is six weeks away. She has 80 products and a notebook. Last year she ordered too many kurti sets and her dupattas sold out in three days. Big stores have forecasting software. She has a hunch. StockWise gives her that help, in plain words."

## 0:20 - 0:50  Upload and auto-detect
Show the app. Point at the green banner.
> "She uploads her sales sheet. StockWise reads the product names, works out this is an ethnic-wear boutique, and sets sensible defaults: longer supplier times, and starting festival assumptions that her own history will replace."

Say: the cleaner also fixed repeated rows and odd spikes (Data check tab, only if asked).

## 0:50 - 1:30  The shopping list
Shopping list tab. Show the status column and the top metrics.
> "Her shopping list, most urgent first. Orders due this week, orders that can wait, and here, a product she should not reorder at all."

Point at **Kurti Set: 158 days of stock, about Rs 3.4 lakh sitting on the shelf.**
> "That is exactly the cash that got stuck last year."

Open the **Item forecast** tab, choose **Festive Dupatta**.
- Chart: "Past sales in blue, forecast in amber with a likely range, and Diwali marked."
- 7 / 15 / 30 day numbers: "What she can expect to sell in the next week, fortnight and month."
- **Why we suggest this** panel: "Every number has a reason she can read: trend, festival, supplier time, stock, and how accurate the model was."

## 1:30 - 1:55  "Your call"
Back in the Shopping list tab. In the table, set Festive Dupatta **Forecast change %** to **30**.
> "She thinks this year will be bigger. She changes one number, and the order quantity goes up and the reorder date moves a week earlier. The plan adjusts around her. No black box."
(In my test: 206 units -> 282 units, reorder date 9 Oct -> 2 Oct.)

## 1:55 - 2:25  CashGuard (your differentiator)
Scroll to CashGuard. Type a budget of **150000**.
> "Meera does not have unlimited cash. She enters what she can spend. StockWise funds the most urgent orders first, buys part of the next one, and tells her the rest can wait until their reorder dates. It is not just 'what to order', it is 'what can I afford to order'."

## 2:25 - 2:50  Does it actually work?
Open **Does it work?** tab.
> "We test every forecast on weeks it has not seen, against a plain average. And we replay the last 12 weeks: ordering with StockWise versus ordering by gut feeling."
Click **Run the replay**. Say it plainly:
> "StockWise loses fewer sales. The honest trade-off is it carries a bit more stock, and the 'how careful' slider controls that. This is synthetic data, so it demonstrates the method, not a guaranteed result."

## 2:50 - 3:00  Close
> "Right stock. Right time. Right decision. It works for any shop: switch to the grocery demo and it adapts. It handles several stores, and suggests new products to test, with evidence. Thank you."

(If you have time or a question: Companies tab with "2 stores", and New product ideas tab, "From your own sales".)

---

## Likely questions, and honest answers
- **Is this real data?** "Synthetic for the demo, so we can show the data problems and festivals. Please try it on a real sales sheet." (If you can get one consented sheet before the event, use it.)
- **How accurate is it?** "On the demo data it beats a plain average, shown on the proof tab. We would measure it again on each real shop's data."
- **Festival dates?** "Approximate for lunar festivals. Sellers can upload their own calendar."
- **New products with no history?** "We cannot forecast those honestly. We borrow patterns from similar products, widen the range, and the new-product ideas are suggestions to test with a small batch."
- **Privacy?** "Only synthetic or consented data, kept within the session."
- **Why not just a chatbot?** "Sellers need numbers they can check and change. Every suggestion shows its reason and can be overridden."

## Do not say
- Do not quote the deck's "120 dupattas by 20 Oct" as app output. It is an illustration; the app shows its own numbers.
- Do not promise exact accuracy or savings.
- Do not run Google Trends or Claude ideas live unless you have tested the venue internet. Use screenshots.
