"""Central configuration for the screener."""

NSE_SUFFIX = ".NS"
BSE_SUFFIX = ".BO"

# Index tickers
NIFTY50     = "^NSEI"
BANKNIFTY   = "^NSEBANK"
INDIA_VIX   = "^INDIAVIX"
SENSEX      = "^BSESN"
NIFTY_IT    = "^CNXIT"
NIFTY_PHARMA = "^CNXPHARMA"
NIFTY_AUTO  = "^CNXAUTO"
NIFTY_METAL = "^CNXMETAL"
NIFTY_REALTY = "^CNXREALTY"
NIFTY_ENERGY = "^CNXENERGY"
NIFTY_FMCG  = "^CNXFMCG"
NIFTY_PSE   = "^CNXPSE"

USDINR      = "USDINR=X"
CRUDE_OIL   = "CL=F"
GOLD        = "GC=F"
US10Y       = "^TNX"

# Technical periods
EMA_PERIODS = [20, 50, 100, 200]
RSI_PERIOD  = 14
MACD_FAST   = 12
MACD_SLOW   = 26
MACD_SIGNAL = 9
BB_PERIOD   = 20
BB_STD      = 2
ATR_PERIOD  = 14
VOLUME_MA   = 20

# Decision thresholds
RSI_OVERSOLD    = 35
RSI_OVERBOUGHT  = 70
RSI_NEUTRAL_LOW = 45
RSI_NEUTRAL_HIGH = 65

# Sector mapping for NSE
SECTOR_MAP = {
    "Banking": ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", "INDUSINDBK",
                "BANKBARODA", "PNB", "CANBK", "UNIONBANK", "FEDERALBNK", "IDFCFIRSTB"],
    "NBFC": ["BAJFINANCE", "BAJAJFINSV", "CHOLAFIN", "MUTHOOTFIN", "MANAPPURAM",
             "M&MFIN", "LICSGFIN", "PNBHOUSING"],
    "IT": ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM", "LTIM", "MPHASIS",
           "COFORGE", "PERSISTENT", "OFSS"],
    "Pharma": ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "TORNTPHARM",
               "AUROPHARMA", "LUPIN", "BIOCON", "ALKEM", "IPCA"],
    "Auto": ["MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "HEROMOTOCO",
             "EICHERMOT", "ASHOKLEY", "TVSMOTOR", "BALKRISIND"],
    "FMCG": ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR",
              "MARICO", "GODREJCP", "EMAMILTD", "TATACONSUM"],
    "Metals": ["TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "NMDC",
               "COALINDIA", "SAIL", "NATIONALUM", "HINDCOPPER"],
    "Power": ["NTPC", "POWERGRID", "ADANIPOWER", "TATAPOWER", "CESC",
              "TORNTPOWER", "NHPC", "SJVN", "RECLTD", "PFC"],
    "Capital Goods": ["L&T", "SIEMENS", "ABB", "BHEL", "THERMAX",
                      "CUMMINSIND", "VOLTAS", "HAVELLS", "POLYCAB"],
    "Defence": ["HAL", "BEL", "BHEL", "MIDHANI", "GRSE", "COCHINSHIP",
                "MTAR", "PARAS", "DRAFTFCB"],
    "Infra/Railways": ["IRFC", "IRCON", "RVNL", "RITES", "NBCC",
                        "KEC", "KALPATPOWR", "ENGINERSIN", "AHLUCONT"],
    "Cement": ["ULTRACEMCO", "SHREECEM", "AMBUJACEM", "ACC", "RAMCOCEM",
               "DALMIACEM", "HEIDELBERG", "JKCEMENT"],
    "Chemicals": ["SRF", "PIDILITIND", "AAVAS", "DEEPAKNTR", "ATUL",
                  "NAVIN", "VINATI", "AARTIIND", "BALCHEMICAL"],
    "Real Estate": ["DLF", "GODREJPROP", "PRESTIGE", "OBEROIRLTY",
                    "BRIGADE", "PHOENIXLTD", "MAHLIFE", "KOLTEPATIL"],
    "Oil & Gas": ["RELIANCE", "ONGC", "IOC", "BPCL", "HPCL",
                  "GAIL", "MGL", "IGL", "ATGL"],
    "Consumption": ["TITAN", "JUBLFOOD", "DMART", "VBL", "MCDOWELL-N",
                    "TRENT", "ABFRL", "PAGEIND", "WHIRLPOOL"],
}

# Popular NSE stocks for quick search (sidebar buttons)
POPULAR_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR",
    "SBIN", "BAJFINANCE", "BHARTIARTL", "KOTAKBANK", "ITC", "LT",
    "HCLTECH", "ASIANPAINT", "AXISBANK", "MARUTI", "SUNPHARMA", "TITAN",
    "BAJAJFINSV", "WIPRO", "ULTRACEMCO", "NTPC", "POWERGRID", "TATAMOTORS",
    "M&M", "NESTLEIND", "TECHM", "DIVISLAB", "DRREDDY", "CIPLA",
    "TATASTEEL", "JSWSTEEL", "HINDALCO", "ADANIENT", "ADANIPORTS",
    "GRASIM", "INDUSINDBK", "EICHERMOT", "COALINDIA", "VEDL",
    "HAL", "BEL", "IRFC", "RVNL", "IRCON", "NHPC", "RECLTD", "PFC",
    "DMART", "TRENT", "VBL", "JUBLFOOD", "PAGEIND",
]

# ── Cap-wise stock lists ──────────────────────────────────────────────────────

# Nifty 50 constituents
NIFTY50_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR",
    "SBIN", "BAJFINANCE", "BHARTIARTL", "KOTAKBANK", "ITC", "LT",
    "HCLTECH", "ASIANPAINT", "AXISBANK", "MARUTI", "SUNPHARMA", "TITAN",
    "BAJAJFINSV", "WIPRO", "ULTRACEMCO", "NTPC", "POWERGRID", "TATAMOTORS",
    "M&M", "NESTLEIND", "TECHM", "DIVISLAB", "DRREDDY", "CIPLA",
    "TATASTEEL", "HINDALCO", "ADANIENT", "ADANIPORTS", "GRASIM",
    "INDUSINDBK", "EICHERMOT", "COALINDIA", "VEDL", "BPCL",
    "ONGC", "JSWSTEEL", "TATACONSUM", "APOLLOHOSP", "HEROMOTOCO",
    "BRITANNIA", "SBILIFE", "HDFCLIFE", "BAJAJ-AUTO", "SHRIRAMFIN",
]

# Nifty Next 50 (large caps outside Nifty 50)
NIFTY_NEXT50_STOCKS = [
    "SIEMENS", "HAVELLS", "ABB", "GODREJCP", "PIDILITIND",
    "MUTHOOTFIN", "CHOLAFIN", "ZOMATO", "NYKAA", "PAYTM",
    "HAL", "BEL", "IRFC", "RECLTD", "PFC", "NHPC",
    "RVNL", "IRCON", "NBCC", "RITES",
    "DLF", "GODREJPROP", "PRESTIGE", "OBEROIRLTY",
    "TORNTPHARM", "AUROPHARMA", "LUPIN", "ALKEM",
    "TVSMOTOR", "ASHOKLEY", "BALKRISIND",
    "DMART", "TRENT", "VBL", "JUBLFOOD",
    "PERSISTENT", "LTIM", "MPHASIS", "COFORGE",
    "SRF", "ATUL", "DEEPAKNTR",
    "AMBUJACEM", "ACC", "SHREECEM",
    "ADANIPOWER", "TATAPOWER", "CESC",
    "BANKBARODA", "IDFCFIRSTB",
]

# Nifty Midcap 100 representative stocks
NIFTY_MIDCAP_STOCKS = [
    "KALYANKJIL", "SUPREMEIND", "WHIRLPOOL", "DIXON", "AMBER",
    "ZYDUSLIFE", "IPCA", "TORNTPOWER", "SJVN",
    "FEDERALBNK", "UNIONBANK", "CANBK", "PNB",
    "LICHSGFIN", "PNBHOUSING", "M&MFIN", "MANAPPURAM",
    "MFSL", "POLICYBZR",
    "BRIGADE", "PHOENIXLTD", "MAHLIFE", "KOLTEPATIL",
    "RAMCOCEM", "DALMIACEM", "JKCEMENT",
    "MARICO", "DABUR", "EMAMILTD", "GODREJAGRO",
    "CUMMINSIND", "THERMAX", "VOLTAS", "POLYCAB", "KEI",
    "KEC", "KALPATPOWR", "ENGINERSIN", "AHLUCONT",
    "NATIONALUM", "HINDCOPPER", "SAIL", "NMDC",
    "MGL", "IGL", "ATGL",
    "MTAR", "GRSE", "COCHINSHIP", "MIDHANI",
    "PAGEIND", "ABFRL", "MCDOWELL-N",
    "OFSS", "KPITTECH", "TATAELXSI", "LTTS",
    "NAVIN", "VINATI", "AARTIIND",
]

# Nifty Smallcap 100 representative stocks
NIFTY_SMALLCAP_STOCKS = [
    "RATNAMANI", "FINEORG", "GALAXYSURF", "BALAMINES",
    "HLEGLAS", "NUVOCO", "SAPPHIRE", "JKPAPER",
    "IDFCFIRSTB", "UJJIVANSFB", "SURYODAY", "EQUITASBNK",
    "AKZOINDIA", "BASF", "NOCIL", "TATACHEM",
    "JSWENERGY", "INOXWIND", "WEBSOL", "BOROSCI",
    "CRAFTSMAN", "ELECON", "TIMKEN", "SCHAEFFLER",
    "METROPOLIS", "THYROCARE", "KRSNAA", "VIJAYA",
    "NIACL", "GICRE", "STARHEALTH",
    "RAINBOW", "KFINTECH", "CAMS",
    "JUSTDIAL", "INDIAMART", "NAUKRI",
    "CLEAN", "TARSONS", "NEOGEN",
    "BIKAJI", "ZYDUSWELL", "HONASA",
    "CAMPUS", "BATA", "RELAXO",
    "GAEL", "VADILALIND", "TASTY",
    "CARBORUNIV", "GRINDWELL", "AIA",
]

# Combined large cap list (Nifty 50 + Next 50)
LARGE_CAP_STOCKS = list(dict.fromkeys(NIFTY50_STOCKS + NIFTY_NEXT50_STOCKS))

MARKET_CAP_CATEGORIES = {
    "Large Cap": 200_000,  # > 20,000 Cr
    "Mid Cap":   20_000,   # 5,000–20,000 Cr
    "Small Cap": 0,        # < 5,000 Cr
}

# Screener preset groups — used in multi-stock screener dropdown
SCREENER_PRESETS = {
    # By index / cap
    "Nifty 50":               NIFTY50_STOCKS,
    "Nifty Next 50 (Large Cap)": NIFTY_NEXT50_STOCKS,
    "All Large Cap (Nifty 100)": LARGE_CAP_STOCKS,
    "Nifty Midcap 100":       NIFTY_MIDCAP_STOCKS,
    "Nifty Smallcap 100":     NIFTY_SMALLCAP_STOCKS,
    # By sector (reuse SECTOR_MAP)
    **{f"Sector — {k}": v for k, v in SECTOR_MAP.items()},
}

NEWS_RSS_FEEDS = [
    "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    "https://www.moneycontrol.com/rss/business.xml",
    "https://www.business-standard.com/rss/markets-106.rss",
]

# ── Symbol → Company Name lookup (for autocomplete search) ───────────────────
# Format: "SYMBOL": "Company Name"
NSE_SYMBOL_MAP: dict[str, str] = {
    # Nifty 50
    "RELIANCE":     "Reliance Industries",
    "TCS":          "Tata Consultancy Services",
    "HDFCBANK":     "HDFC Bank",
    "ICICIBANK":    "ICICI Bank",
    "INFY":         "Infosys",
    "HINDUNILVR":   "Hindustan Unilever",
    "SBIN":         "State Bank of India",
    "BAJFINANCE":   "Bajaj Finance",
    "BHARTIARTL":   "Bharti Airtel",
    "KOTAKBANK":    "Kotak Mahindra Bank",
    "ITC":          "ITC Limited",
    "LT":           "Larsen & Toubro",
    "HCLTECH":      "HCL Technologies",
    "ASIANPAINT":   "Asian Paints",
    "AXISBANK":     "Axis Bank",
    "MARUTI":       "Maruti Suzuki",
    "SUNPHARMA":    "Sun Pharmaceutical",
    "TITAN":        "Titan Company",
    "BAJAJFINSV":   "Bajaj Finserv",
    "WIPRO":        "Wipro",
    "ULTRACEMCO":   "UltraTech Cement",
    "NTPC":         "NTPC",
    "POWERGRID":    "Power Grid Corporation",
    "TATAMOTORS":   "Tata Motors",
    "M&M":          "Mahindra & Mahindra",
    "NESTLEIND":    "Nestle India",
    "TECHM":        "Tech Mahindra",
    "DIVISLAB":     "Divi's Laboratories",
    "DRREDDY":      "Dr. Reddy's Laboratories",
    "CIPLA":        "Cipla",
    "TATASTEEL":    "Tata Steel",
    "HINDALCO":     "Hindalco Industries",
    "ADANIENT":     "Adani Enterprises",
    "ADANIPORTS":   "Adani Ports & SEZ",
    "GRASIM":       "Grasim Industries",
    "INDUSINDBK":   "IndusInd Bank",
    "EICHERMOT":    "Eicher Motors",
    "COALINDIA":    "Coal India",
    "VEDL":         "Vedanta",
    "BPCL":         "Bharat Petroleum",
    "ONGC":         "Oil & Natural Gas Corporation",
    "JSWSTEEL":     "JSW Steel",
    "TATACONSUM":   "Tata Consumer Products",
    "APOLLOHOSP":   "Apollo Hospitals",
    "HEROMOTOCO":   "Hero MotoCorp",
    "BRITANNIA":    "Britannia Industries",
    "SBILIFE":      "SBI Life Insurance",
    "HDFCLIFE":     "HDFC Life Insurance",
    "BAJAJ-AUTO":   "Bajaj Auto",
    "SHRIRAMFIN":   "Shriram Finance",
    # Nifty Next 50 / Large Cap
    "SIEMENS":      "Siemens India",
    "HAVELLS":      "Havells India",
    "ABB":          "ABB India",
    "GODREJCP":     "Godrej Consumer Products",
    "PIDILITIND":   "Pidilite Industries",
    "MUTHOOTFIN":   "Muthoot Finance",
    "CHOLAFIN":     "Cholamandalam Investment",
    "ZOMATO":       "Zomato",
    "NYKAA":        "FSN E-Commerce (Nykaa)",
    "PAYTM":        "One 97 Communications (Paytm)",
    "HAL":          "Hindustan Aeronautics",
    "BEL":          "Bharat Electronics",
    "IRFC":         "Indian Railway Finance Corp",
    "RECLTD":       "REC Limited",
    "PFC":          "Power Finance Corporation",
    "NHPC":         "NHPC",
    "RVNL":         "Rail Vikas Nigam",
    "IRCON":        "Ircon International",
    "NBCC":         "NBCC (India)",
    "RITES":        "RITES",
    "DLF":          "DLF",
    "GODREJPROP":   "Godrej Properties",
    "PRESTIGE":     "Prestige Estates Projects",
    "OBEROIRLTY":   "Oberoi Realty",
    "TORNTPHARM":   "Torrent Pharmaceuticals",
    "AUROPHARMA":   "Aurobindo Pharma",
    "LUPIN":        "Lupin",
    "ALKEM":        "Alkem Laboratories",
    "TVSMOTOR":     "TVS Motor Company",
    "ASHOKLEY":     "Ashok Leyland",
    "BALKRISIND":   "Balkrishna Industries",
    "DMART":        "Avenue Supermarts (DMart)",
    "TRENT":        "Trent",
    "VBL":          "Varun Beverages",
    "JUBLFOOD":     "Jubilant FoodWorks",
    "PERSISTENT":   "Persistent Systems",
    "LTIM":         "LTIMindtree",
    "MPHASIS":      "Mphasis",
    "COFORGE":      "Coforge",
    "SRF":          "SRF",
    "ATUL":         "Atul",
    "DEEPAKNTR":    "Deepak Nitrite",
    "AMBUJACEM":    "Ambuja Cements",
    "ACC":          "ACC",
    "SHREECEM":     "Shree Cement",
    "ADANIPOWER":   "Adani Power",
    "TATAPOWER":    "Tata Power",
    "CESC":         "CESC",
    "BANKBARODA":   "Bank of Baroda",
    "IDFCFIRSTB":   "IDFC First Bank",
    # Midcap
    "KALYANKJIL":   "Kalyan Jewellers",
    "SUPREMEIND":   "Supreme Industries",
    "WHIRLPOOL":    "Whirlpool of India",
    "DIXON":        "Dixon Technologies",
    "AMBER":        "Amber Enterprises",
    "ZYDUSLIFE":    "Zydus Lifesciences",
    "IPCA":         "IPCA Laboratories",
    "TORNTPOWER":   "Torrent Power",
    "SJVN":         "SJVN",
    "FEDERALBNK":   "Federal Bank",
    "UNIONBANK":    "Union Bank of India",
    "CANBK":        "Canara Bank",
    "PNB":          "Punjab National Bank",
    "LICHSGFIN":    "LIC Housing Finance",
    "PNBHOUSING":   "PNB Housing Finance",
    "M&MFIN":       "Mahindra & Mahindra Financial",
    "MANAPPURAM":   "Manappuram Finance",
    "MFSL":         "Max Financial Services",
    "POLICYBZR":    "PB Fintech (PolicyBazaar)",
    "BRIGADE":      "Brigade Enterprises",
    "PHOENIXLTD":   "Phoenix Mills",
    "MAHLIFE":      "Mahindra Lifespace",
    "KOLTEPATIL":   "Kolte-Patil Developers",
    "RAMCOCEM":     "Ramco Cements",
    "DALMIACEM":    "Dalmia Bharat",
    "JKCEMENT":     "JK Cement",
    "MARICO":       "Marico",
    "DABUR":        "Dabur India",
    "EMAMILTD":     "Emami",
    "CUMMINSIND":   "Cummins India",
    "THERMAX":      "Thermax",
    "VOLTAS":       "Voltas",
    "POLYCAB":      "Polycab India",
    "KEI":          "KEI Industries",
    "KEC":          "KEC International",
    "KALPATPOWR":   "Kalpataru Projects",
    "ENGINERSIN":   "Engineers India",
    "AHLUCONT":     "Ahluwalia Contracts",
    "NATIONALUM":   "National Aluminium",
    "HINDCOPPER":   "Hindustan Copper",
    "SAIL":         "Steel Authority of India",
    "NMDC":         "NMDC",
    "MGL":          "Mahanagar Gas",
    "IGL":          "Indraprastha Gas",
    "ATGL":         "Adani Total Gas",
    "MTAR":         "MTAR Technologies",
    "GRSE":         "Garden Reach Shipbuilders",
    "COCHINSHIP":   "Cochin Shipyard",
    "MIDHANI":      "Mishra Dhatu Nigam",
    "PAGEIND":      "Page Industries",
    "ABFRL":        "Aditya Birla Fashion",
    "MCDOWELL-N":   "United Spirits",
    "OFSS":         "Oracle Financial Services",
    "KPITTECH":     "KPIT Technologies",
    "TATAELXSI":    "Tata Elxsi",
    "LTTS":         "L&T Technology Services",
    "NAVIN":        "Navin Fluorine",
    "VINATI":       "Vinati Organics",
    "AARTIIND":     "Aarti Industries",
    # Smallcap / others
    "IOLCP":        "IOL Chemicals & Pharmaceuticals",
    "RATNAMANI":    "Ratnamani Metals & Tubes",
    "FINEORG":      "Fine Organic Industries",
    "GALAXYSURF":   "Galaxy Surfactants",
    "BALAMINES":    "Balaji Amines",
    "AKZOINDIA":    "Akzo Nobel India",
    "JSWENERGY":    "JSW Energy",
    "CRAFTSMAN":    "Craftsman Automation",
    "ELECON":       "Elecon Engineering",
    "TIMKEN":       "Timken India",
    "SCHAEFFLER":   "Schaeffler India",
    "METROPOLIS":   "Metropolis Healthcare",
    "THYROCARE":    "Thyrocare Technologies",
    "RAINBOW":      "Rainbow Children's Medicare",
    "KFINTECH":     "KFin Technologies",
    "CAMS":         "CAMS",
    "JUSTDIAL":     "Just Dial",
    "INDIAMART":    "IndiaMART InterMESH",
    "NAUKRI":       "Info Edge (Naukri)",
    "BIKAJI":       "Bikaji Foods",
    "ZYDUSWELL":    "Zydus Wellness",
    "BATA":         "Bata India",
    "RELAXO":       "Relaxo Footwears",
    "CARBORUNIV":   "Carborundum Universal",
    "GRINDWELL":    "Grindwell Norton",
    "GAIL":         "GAIL (India)",
    "IOC":          "Indian Oil Corporation",
    "HPCL":         "Hindustan Petroleum",
    "CONCOR":       "Container Corporation of India",
    "IRCTC":        "Indian Railway Catering & Tourism",
    "LODHA":        "Macrotech Developers (Lodha)",
    "NUVOCO":       "Nuvoco Vistas",
    "JKPAPER":      "JK Paper",
    "NOCIL":        "NOCIL",
    "TATACHEM":     "Tata Chemicals",
    "BOROSCI":      "Borosil Scientific",
    "HONASA":       "Honasa Consumer (Mamaearth)",
    "CAMPUS":       "Campus Activewear",
    "STARHEALTH":   "Star Health Insurance",
    "GICRE":        "General Insurance Corporation",
    "NIACL":        "New India Assurance",
    "CLEAN":        "Clean Science & Technology",
    "TARSONS":      "Tarsons Products",
    "NEOGEN":       "Neogen Chemicals",
}

# Searchable list: "SYMBOL — Company Name" for selectbox display
NSE_SEARCH_OPTIONS: list[str] = sorted(
    [f"{sym} — {name}" for sym, name in NSE_SYMBOL_MAP.items()]
)

def symbol_from_option(option: str) -> str:
    """Extract NSE symbol from a selectbox option string."""
    return option.split(" — ")[0].strip()
