# Active foreign principal scraper

Got a test task during the job interview to write scraper for 
[www.fara.gov](www.fara.gov) using [Scrapy](https://www.scrapy.org).
___

Data format: 

```json
[
  {
    "registrant": "International Trade & Development Agency, Inc.",
    "url": "https://efile.fara.gov/pls/apex/f?p=171:200:8832334613063::NO:RP,200:P200_REG_NUMBER,P200_DOC_TYPE,P200_COUNTRY:3690,Exhibit%20AB,TAIWAN",
    "address": "Washington",
    "reg_num": "3690",
    "country": "TAIWAN",
    "foreign_principal": "Taipei Economic & Cultural Representative Office in the U.S.",
    "date": "1995-08-28 00:00:00",
    "exhibit_urls": [
      "http://www.fara.gov/docs/3690-Exhibit-AB-20160614-10.pdf",
      ...
    ],
    "state": "DC"
  },
  ...
]
```
___

Project is not maintained - use at your own risk. However the html markup of the site doesn't seem to be 
changed during the last decade - so there is a good chance that the script will work.
