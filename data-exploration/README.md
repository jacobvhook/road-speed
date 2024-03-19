## What is this folder?

This folder contains the outputs of some early data wrangling, together with
some naive models against which we can test the performance of better models
that we will develop.

You should first run the code in `nyc_accidents.ipynb`. That will create the
dataset that is used in `mwe.ipynb`. In order to run `nyc_accidents.ipynb`, you
will need to get an app token from NYC Open Data, create a file named `.env` in
this folder and add the following content:

```
NYC_OPENDATA_APPTOKEN=<insert your app token here>
```
