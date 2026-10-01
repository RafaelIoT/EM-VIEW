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
Select countries with the searchable sidebar checkboxes. **Select all** and
**Clear all** apply to the current region/subregion, even while searching.
Hidden country choices are preserved when searching or changing geography;
**Reset** selects all countries again. Country selections apply to every view.

### Compare countries

Open **Country comparison** after loading your workbook. Check countries in the sidebar and choose
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
value at or before the end year within the retrieved series for the context table
only. The query covers every selected event start year and at least five years
before the reference year; its year range is displayed.

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

### Customize and export a comparison

**Customize charts** controls country-bar orientation, category ordering, color
palette, logarithmic axes, and value labels. Annual lines preserve gaps for years
without records. Country colors stay stable when countries are deselected.
**Event records** lets you inspect all source columns and search by ID, name,
location, country or type. This table's search does not change the comparison.

Download the country summary or displayed event records as CSV, or download a
full ZIP containing country/type/year summaries, every analyzed source row,
annual country indicators (if loaded), and `analysis.json` with filters, units,
normalization and source provenance. Blank CSV cells remain unavailable. Raw
source damage columns keep their original thousands-of-US$ units; summarized
damage Values are in US$.

### Run regression checks

```bash
python -m unittest discover -s tests -v
```

Tests cover date boundaries and uncertainty, denominators and missing impacts,
country/year normalizations, World Bank pagination and failures, chart gaps,
exports, and Streamlit navigation and control changes. Tests use synthetic data;
no EM-DAT workbook is committed to this repository.

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
