# Road safety

The purpose of this project is to use regression modeling and neural networks to
to predict accident rates in New York City using public road data and other
geological features, and to identify key road infrastructures that can improve
safety in the cheapest way possible.

## Authors

- [Assaf Bar-Natan](https://www.linkedin.com/in/assaf-bar-natan-b61556209)
- [Jesse Frohlich](https://www.linkedin.com/in/jessefrohlich)
- [Jacob van Hook](https://www.linkedin.com/in/jacob-van-hook-4484b2288/)
- [Pedro Lemos](https://www.linkedin.com/in/pedro-j-lemos/)
- [Guillermo Sanmarco](https://www.linkedin.com/in/guillermo-sanmarco-050904239/)

## Description

### Overview

Traffic accidents are a leading cause of death and injury amongst Americans
under the age of 54. A significant portion of these accidents are preventable by
changing driver attitudes and improving in-vehicle safety measures, but also by
creating better public infrastructure that encourages safe practices.

The goal of this project is to develop a predictive model that will assess the
change in collision rates in a given road section of New York City after changes
in road features are implemented.

**paragraph about using ML to identify what these practices are** ** paragraph
about finding problem areas to improve**

**Stakeholders:** General public, local politicians, neighbourhood advocacy
groups, commuters, urban planners, road design engineers, NYC police, insurance
companies

**KPIs for accident rate forecasting:** mean squared error (MSE) and mean
absolute error (MAE) between the true accident rate and predicted accident rate.

### Datasets

Our data for this project is coming from
[NYC Open Data](https://opendata.cityofnewyork.us/). Their data includes
features such as:

- Road Width
- Traffic Volumes
- Existence of Speed Humps
- Existence of Bike Lanes
- Existence of Trees
- Car accident locations and times

The dataset used to train and test our models is built by joining and
aggregating information contained in different data sources. This is done
automatically by the script `src/data_generator.py`. This script will be
executed if you run `make` in the top directory.

### Approach

We have several proposed models we are going to test to see how well they
predict the rate of collisions on a given road segment.

- **Baseline Model**: This model always predicts the mean accident rate across
  the entire city for every road segment, regardless of features. This is
  important to have because it gives us a basis of comparison by which to
  measure our other models. If a model cannot do better than just predicting the
  average every time, it is likely not a very good model.
- **Linear Regression**: This straightforward model uses linear regression and
  predicts a linear relationship between features, or combinations thereof, and
  the accident rate. This is also a good basis of comparison and can be used to
  assess the effectiveness of more complicated models.
- **Random Forest Regression**: We also want to test the effectiveness of a
  random forest regressor. This may prove useful as a way to determine
  relationships which we would not be able to see through standard linear
  regressions.
- **K-Nearest Neighbors Regression**: We want to look at the predictive power of
  a K-Nearest Neighbors model because roads with similar features are likely to
  have similar accident rates and can therefore serve as a predictor.

## [Web app](https://streamlit.io/)

## Future Iterations

## Citations

## Project outline

Analyse features of a road's design, and build a model to predict the safety of
the road, either using KSI metrics or average/ maximum vehicle speed as proxies
for safety & comfort.

### Proposed Data Features

TODO: Add data sources to the following features

- Lane width
- Number of lanes
  - Open Street Maps (OSM)
- Corridor width (related to building setback)
- Presence of trees
  - OSM
  - [Toronto's Open Data][TOD]
- Existence and style of a median (painted, vegetation, concrete)
- Presence and type of cycling infrastructure
  - OSM
- Presence and quality of sidewalks (number, width)
  - OSM (sidewalk width is usually not included)
- Parallel/ angle parking availability?
  - OSM (sometimes)
- Parking & bike lane ordering
- Traffic light / stop sign density (km^-1)
- Road surface type (asphalt, paving stones, gravel)
  - OSM
- Road quality (potholes, construction presence)
- Presence of streetlights
  - OSM
- Surrounding land use (business, commercial, industrial, residential, mixed)
  - OSM
- Population density of the surrounding area
- Traffic volume sorted by mode
- Presence of trucks/ weight restrictions
- Presence of dedicated bus lanes
  - OSM
- Presence of a bus route
  - OSM
- Speed restrictions
  - OSM

### Other points

Since many pedestrian deaths are occurring at nighttime, it may be worth the
effort to predict road speed / safety as a function of time of day (or
daytime/nighttime, on-peak/ off-peak)

### Notes on data sources

#### OSM data

Data from open street maps is publicly maintained, so different areas will have
different degrees of completeness. The [Python module OSMnx][OSMnx] can be used
to fetch and visualize OSM data.

## Usage

To set up the working environment, it is strongly encouraged to set up a virtual
environment, say with `pyenv`:

```
$ python -m venv .venv
```

To activate the virtual environment, source the following:

```
$ source .venv/bin/activate
```

Finally, you can install the packages locally via `pip`:

```
pip install -r requirements.txt
```

The `OpenDataDownloader` class in `src` takes an optional app token that can be
obtained from the [NYC Open Data website](https://data.cityofnewyork.us). To run
some of the notebooks, you will need to store this app token in a file named
`.env` in the top directory with the following content:

```
NYC_OPENDATA_APPTOKEN=<insert your app token here>
```

## Contributing

This project uses [`pre-commit`](https://pre-commit.com/) to ensure code
formatting is consistent before committing. The currently-used hooks are:

- [`black`](https://black.readthedocs.io/en/stable) for `*.py` or `*.ipynb`
  files.
- [`prettier`](https://prettier.io/) (with `--prose-wrap always` for markdown)

To set up the hooks on your local machine, install `pre-commit`, then run
`pre-commit install` to install the formatters that will run before each commit.

[TOD]: https://open.toronto.ca/dataset/street-tree-data/
[OSMnx]: https://pygis.io/docs/d_access_osm.html
