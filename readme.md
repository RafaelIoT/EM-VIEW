# EM-VIEW: A Community Dashboard for your EM-DAT Data

![Preview](images/emview_preview.png)


This is a [Streamlit](https://streamlit.io/) Web App designed to visualize 
the [EM-DAT International Disaster Database](https://www.emdat.be/) data 
contained in your official EM-DAT xlsx file. EM-VIEW has multiple tabs with 
specific features responding to filters:
- Metric view: impact statistics, disaggregated by disaster types;
- Country comparison: grouped impact charts, per-event averages and medians,
  annual trends, and reporting coverage for multiple countries;
- Table view: the EM-DAT dataframe that can be filtered by column names;
- Map view: global or regional impact maps by country;
- Time view: yearly-aggregated timeseries of impact, with multiple stacking 
options.

You can download the EM-DAT data by registering on the 
[EM-DAT Data Portal](https://public.emdat.be/).

## Use the app on Streamlit Community Cloud

Visit https://emview.streamlit.app/

## Install, Use, and Customize the App Locally 

The app relies on streamlit version 1.52.

### Install Dependencies:
   ```bash
   pip install -r requirements.txt
   ```

Check `requirements.txt` for details.

### Filter a period and disaster types

The sidebar filters all views by event start year, including events with an
unknown end year. Enable **Use exact dates** for an inclusive start/end date
range, or choose **Overlaps period** to include events spanning the period.
Partial start dates are included when their known month/year could fall in the
period; turn off **Include partial start dates** to require a precise start date.
Unknown end dates use the start-date interval and are not assumed ongoing.
Select disaster groups and types directly, or use a classification-key prefix
with `*` wildcards. Empty group/type selections include all categories.

### Compare countries

Open **Country comparison** after loading your workbook. Choose countries and
impact measures, then compare totals, means per event, or medians per event.
Means default to events with a reported value, with an explicit option to divide
the observed sum by all events. Blank impacts remain missing; explicit zero is
a reported value. Reporting coverage is included in chart hovers and a table.
Damage charts convert EM-DAT's thousands of US dollars to US dollars.

### Add population and GDP context

In Country comparison, **Load country context** retrieves annual
World Bank WDI population (`SP.POP.TOTL`), GDP in current US dollars
(`NY.GDP.MKTP.CD`), and GDP per capita (`NY.GDP.PCAP.CD`). Requests are cached for
24 hours; no API key is required. Offline/API failures leave absolute comparisons
available. Context values show their source years, using the latest reported
value at or before the end year for the context table only.

**Per 100,000 residents** divides each event's impact by that country's population
in the event's start year. **% of event-year GDP** is available when the only
selected metric is damage in current US dollars, avoiding mismatched inflation
bases. Rates require exact country/start-year matches; missing denominators are
excluded and reported in the coverage table. Period totals sum event-year rates,
not shares of a single period population or GDP. Historical countries and years
without WDI observations remain unavailable.

Sources: [World Bank population](https://data.worldbank.org/indicator/SP.POP.TOTL),
[GDP](https://data.worldbank.org/indicator/NY.GDP.MKTP.CD),
[GDP per capita](https://data.worldbank.org/indicator/NY.GDP.PCAP.CD).

### Run App

With streamlit installed, use the following command to run the app:
   ```bash
    streamlit run app.py
   ```

## Licence

MIT, see attached `License` file. This license applies to the content of this 
repository and does not cover the EM-DAT data usage rights. See 
[EM-DAT Terms of Use](https://doc.emdat.be/docs/legal/).

## Acknowledgement

The initial version of EM-VIEW was developed under the EM-DAT project with 
the support of USAID.
