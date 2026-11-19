from .database import query_rows, MONTHS, REGIONS


def prior_month(month: str):
    idx=MONTHS.index(month)
    return MONTHS[idx-1] if idx>0 else None


def sales(region: str, month: str) -> dict:
    prev=prior_month(month)
    rows=query_rows("""SELECT month, SUM(revenue) AS revenue, SUM(units) AS units
      FROM performance WHERE region=? AND month IN (?,?) GROUP BY month ORDER BY month""",
      (region,month,prev or month))
    lookup={r['month']:r for r in rows}
    current=lookup.get(month,{'revenue':0,'units':0})
    previous=lookup.get(prev) if prev else None
    delta=((current['revenue']/previous['revenue']-1)*100) if previous and previous['revenue'] else None
    products=query_rows("""SELECT product, revenue, units FROM performance
      WHERE region=? AND month=? ORDER BY revenue DESC""",(region,month))
    priorproducts=query_rows("""SELECT product, revenue FROM performance WHERE region=? AND month=?""",(region,prev or month))
    pmap={p['product']:p['revenue'] for p in priorproducts}
    for p in products:
        old=pmap.get(p['product'])
        p['previous_revenue']=old if prev else None
        p['change_pct']=round((p['revenue']/old-1)*100,2) if old and prev else None
    return {'current_revenue':round(current['revenue'],2),'previous_revenue':round(previous['revenue'],2) if previous else None,
            'change_pct':round(delta,2) if delta is not None else None,'units':current['units'], 'products':products,
            'evidence':'Monthly revenue and units aggregated from performance table'}


def inventory(region: str, month: str) -> dict:
    rows=query_rows("""SELECT product, stockout_days, units, revenue FROM performance
      WHERE region=? AND month=? ORDER BY stockout_days DESC""",(region,month))
    return {'products':rows,'total_stockout_days':sum(x['stockout_days'] for x in rows),
            'evidence':'Recorded product stockout-days; association does not prove causation'}


def finance(region: str, month: str) -> dict:
    prev=prior_month(month)
    rows=query_rows("""SELECT month, SUM(revenue) AS revenue, SUM(cogs) AS cogs,
      SUM(promo_spend) AS promo_spend FROM performance WHERE region=? AND month IN (?,?)
      GROUP BY month ORDER BY month""",(region,month,prev or month))
    mapped={x['month']:x for x in rows}
    curr=mapped.get(month)
    old=mapped.get(prev) if prev else None
    if not curr: return {'error':'No data'}
    def metrics(row):
        rev=row['revenue'] or 0
        return {'gross_profit':round(rev-row['cogs'],2),
                'gross_margin_pct':round((rev-row['cogs'])/rev*100,2) if rev else None,
                'promo_spend':round(row['promo_spend'],2),
                'promo_rate_pct':round(row['promo_spend']/rev*100,2) if rev else None}
    return {'current':metrics(curr),'previous':metrics(old) if old else None,
            'evidence':'Gross margin = (revenue - COGS) / revenue; promo spend reported separately'}


def trend(region: str) -> list:
    return query_rows("""SELECT month, ROUND(SUM(revenue),2) AS revenue
       FROM performance WHERE region=? GROUP BY month ORDER BY month""",(region,))


def validate_scope(region: str, month: str):
    if region not in REGIONS: raise ValueError(f'Unsupported region: {region}')
    if month not in MONTHS: raise ValueError(f'Unsupported month: {month}')
