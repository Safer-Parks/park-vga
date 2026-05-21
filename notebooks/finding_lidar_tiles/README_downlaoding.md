# Acquiring LiDAR Datasets

## England dataset

I initially used this great [tutorial](https://historicengland.org.uk/content/docs/research/using-ea-lidar-data-pdf/) from Historic England which provides guidance on how to download datasets manually through the Defra web interface; specifically useful is the explanation of the dataset naming conventions for different data products.

However, for this large-scale project, instead of using the web-based download interface, I contacted Defra directly as per the guidance on the data portal, and was given SFTP access to download the dataset in a more streamlined way (along with the required guidance to do so). The web interface downloader is very intuitive and easy to use, but limits downloads to very small subsections (a few tiles), whereas we wanted the entire 2022 composite dataset. SFTP makes this large download task very straighforward.

You can read more about the composite LIDAR dataset [here](https://www.owenboswarva.com/opendata/EA/Environment_Agency_LIDAR_Open_Data_FAQ_v5.pdf).

For calculating example bounding boxes, I used [bbox finder](https://bboxfinder.com/); actual park bounding boxes were calculated in Python from the park boundary geometry.

## Wales dataset

The Wales Lidar dataset can be [downloaded from Datamap Wales](https://datamap.gov.wales/maps/lidar-data-download/); specifically the 32 bit dataset will be comparable to the England Defra dataset.