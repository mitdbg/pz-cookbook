# class Bike:
#     def __init__(self):

import argparse
import json
import os
from pathlib import Path

import gradio as gr
import numpy as np
from PIL import Image

from palimpzest.core.data.datasources import UserSource
from palimpzest.core.elements.records import DataRecord
from palimpzest.core.lib.fields import BooleanField, ListField, ImageFilepathField, NumericField, StringField
from palimpzest.core.lib.schemas import Schema
from palimpzest.constants import Model
from palimpzest.policy import MaxQuality, MinCost, MinTime
from palimpzest.datamanager.datamanager import DataDirectory
from palimpzest.sets import Dataset
from palimpzest.query.processor.config import QueryProcessorConfig
from palimpzest.utils.demo_helpers import print_table


#GO TO LINES 244 ONWARD AND MAKE IT CORRESPOND WITH BIKE LISTINGD


CLOSE_ADDRS = [
    "Cambridge",
    "Belmont",
    "Medford",
    "Somerville",

]
#unneccessary right now.. unless we add a middle address attribute

# FAR_AWAY_ADDRS = [
#     "Newburyport",  
#     "East Bridgewater",  
#     "Amesbury", 
#     "Beverly",
# ]


# def within_two_miles_of_mit(record):
#     # NOTE: I'm using this hard-coded function so that folks w/out a
#     #       Geocoding API key from google can still run this example
#     try:
#         return not any([street.lower() in record.address.lower() for street in FAR_AWAY_ADDRS]) #one line code, need clarity for it
#     except Exception:
#         return False


# def in_price_range(record):
#     try:
#         price = record.price
#         if isinstance(price, str):
#             price = price.strip()
#             price = int(price.replace("$", "").replace(",", ""))
#         return 6e5 < price <= 2e6
#     except Exception:
#         return False
    
def is_good_deal(record: dict):
    price = record["price"]
    if isinstance(price, str):
            price = price.strip()
            price = int(price.replace("$", "").replace(",", ""))
    return price <= 100

def is_close(record: dict):
    address = record["location"]
    return any([street.lower() in address.lower() for street in CLOSE_ADDRS])


# def is_far (record): #unneccessary
#     address = record.location
#     return any([street.lower() in address.lower() for street in FAR_AWAY_ADDRS])







#Bicycle classes


class BikeListingFiles(Schema):
    """The source text and image data for a real estate listing."""

    listing = StringField(desc="The name of the listing")
    text_content = StringField(desc="The content of the listing's text description")
    image_filepaths = ListField(
        element_type=ImageFilepathField,
        desc="A list of the filepaths for each image of the listing",
    )


class TextBikeListing(BikeListingFiles): #solely rely on the text and NO images
    """Represents a real estate listing with specific fields extracted from its text."""

    # address = StringField(desc="The address of the property")
    # price = NumericField(desc="The listed price of the property")

    price = NumericField(desc="The listed price of the property")

    # brand = StringField(desc="The brand of the bike")
    # is_new = BooleanField(desc="True if bicycle is relatively new and fresh and False if otherwiswe") 
    # size = NumericalField (desc="The zie of the bike") #variables that can be determined by images and  text


    seller_name = StringField(desc="The name of the seller")
    seller_id = NumericField(desc="The id of the seller")
    seller_rating = NumericField(desc="The rating of the seller")
    location = StringField(desc="The location of the bike seller")
    description = StringField(desc="The description of the bike")
    description_shortened = StringField(desc="The shortened description of the bike")


class ImageBikeListing(BikeListingFiles): #uses both the Text and Image to computer answer
    """Represents a real estate listing with specific fields extracted from its text and images."""

    # is_modern_and_attractive = BooleanField(
    #     desc="True if the home interior design is modern and attractive and False otherwise"
    # )
    # has_natural_sunlight = BooleanField(
    #     desc="True if the home interior has lots of natural sunlight and False otherwise"
    # )


    is_bike = BooleanField(desc="True if the images show a bike and False otherwise")



    brand = StringField(desc="The brand of the bike")
    is_new = BooleanField(desc="True if the bike is new, and False otherwise")
    size = NumericField(desc="The size of the bike") #variables that can be determined by images and  text


    condition = NumericField (desc="The condition of the bike")
    condition_rating = NumericField(desc="The condition of the bike quantifiied on a 1-10 scale")
    # images = ListField(element_type=StringField, desc="List of Images") #is this neccessary



class BikeListingSource(UserSource): #confirm whether or not its correct
    def __init__(self, dataset_id, listings_dir):
        super().__init__(BikeListingFiles, dataset_id)
        self.listings_dir = listings_dir
        self.listings = sorted(os.listdir(self.listings_dir))

    def copy(self):
        return BikeListingSource(self.dataset_id, self.listings_dir)

    def __len__(self):
        return len(self.listings)

    def get_size(self):
        return sum(file.stat().st_size for file in Path(self.listings_dir).rglob("*"))

    def get_item(self, idx: int):
        # fetch listing
        listing = self.listings[idx]

        # create data record
        dr = DataRecord(self.schema, source_id=listing)
        dr.listing = listing
        dr.image_filepaths = []
        listing_dir = os.path.join(self.listings_dir, listing)
        for file in os.listdir(listing_dir):
            if file.endswith(".txt"):
                with open(os.path.join(listing_dir, file), "rb") as f:
                    dr.text_content = f.read().decode("utf-8")
            elif file.endswith(".png"):
                dr.image_filepaths.append(os.path.join(listing_dir, file))

        return dr
    








    #main File

if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser(description="Run a simple demo")
    parser.add_argument("--viz", default=False, action="store_true", help="Visualize output in Gradio")
    parser.add_argument("--verbose", default=False, action="store_true", help="Print verbose output")
    parser.add_argument("--profile", default=False, action="store_true", help="Profile execution")
    parser.add_argument("--datasetid", type=str, help="The dataset id")
    parser.add_argument(
        "--workload", type=str, help="The workload to run. One of enron, real-estate, medical-schema-matching."
    )
    parser.add_argument(
        "--executor",
        type=str,
        help="The plan executor to use. One of sequential, pipelined_single_thread, pipelined_parallel",
        default="sequential",
    )
    parser.add_argument(
        "--policy",
        type=str,
        help="One of 'mincost', 'mintime', 'maxquality'",
        default="mincost",
    )

    args = parser.parse_args()

    # The user has to indicate the dataset id and the workload
    if args.datasetid is None:
        print("Please provide a dataset id")
        exit(1)
    if args.workload is None:
        print("Please provide a workload")
        exit(1)

    # create directory for profiling data
    if args.profile:
        os.makedirs("profiling-data", exist_ok=True)

    datasetid = args.datasetid
    workload = args.workload
    visualize = args.viz
    verbose = args.verbose
    profile = args.profile
    policy = MaxQuality()
    if args.policy == "mincost":
        policy = MinCost()
    elif args.policy == "mintime":
        policy = MinTime()
    elif args.policy == "maxquality":
        policy = MaxQuality()
    else:
        print("Policy not supported for this demo")
        exit(1)

    if os.getenv("OPENAI_API_KEY") is None and os.getenv("TOGETHER_API_KEY") is None:
        print("WARNING: Both OPENAI_API_KEY and TOGETHER_API_KEY are unset")

    # create pz plan
    #REPLACE WITH BIKE LISTINGS AT LINES 244 ONWORD
    user_dataset_id = f"{datasetid}-user"
    DataDirectory().register_user_source(
        src=BikeListingSource(user_dataset_id, "bike-listings"),
        dataset_id=user_dataset_id,
    )
    plan = Dataset(user_dataset_id, schema=BikeListingFiles)
    plan = plan.convert(TextBikeListing, depends_on="text_content")
    plan = plan.convert(ImageBikeListing, depends_on="image_filepaths")
    # plan = plan.filter(
    #     "The interior is modern and attractive, and has lots of natural sunlight",
    #     depends_on=["is_modern_and_attractive", "has_natural_sunlight"],
    # ) -->do we need
    plan = plan.filter(is_close, depends_on="location") # TODO: update to use is_close
    plan = plan.filter(is_good_deal, depends_on="price") # TODO: update to use is_good_deal
    plan = plan.filter(
        "The bike can be any color!",
    )

    config = QueryProcessorConfig(
        nocache=True,
        verbose=verbose,
        policy=policy,
        execution_strategy=args.executor,
        available_models=[Model.MIXTRAL, Model.GPT_4o_MINI, Model.GPT_4o_MINI_V]
    )
    data_record_collection = plan.run(config)
    print(data_record_collection.to_df())

    # visualize output in Gradio
    if visualize:
        from palimpzest.utils.demo_helpers import print_table

        plan_str = list(data_record_collection.execution_stats.plan_strs.values())[-1]
        fst_imgs, snd_imgs, thrd_imgs, locations, prices = [], [], [], [], [] # init list for ratings = []
        is_news = []
        sizes = []
        condition_strings = []
        condition_ratings = []
        is_bikes = []
        brands = []
        seller_names = []
        seller_ratings = []
        descriptions = []
        shortened_descriptions = []
        for record in data_record_collection:
            locations.append(record.location)
            prices.append(record.price) # also append record.seller_rating to ratings
            is_news.append(record.is_new)
            sizes.append(record.size)
            condition_strings.append(record.condition)
            condition_ratings.append(record.condition_rating)
            is_bikes.append(record.is_bike)
            brands.append(record.brand)
            seller_names.append(record.seller_name)
            seller_ratings.append(record.seller_rating)
            descriptions.append(record.description)
            shortened_descriptions.append(record.description_shortened)

            for idx, img_name in enumerate(["image1.png", "image2.png", "image3.png"]): # img -> image
                path = os.path.join(f"testdata/{datasetid}", record.listing, img_name)
                img = Image.open(path)
                img_arr = np.asarray(img)
                if idx == 0:
                    fst_imgs.append(img_arr)
                elif idx == 1:
                    snd_imgs.append(img_arr)
                elif idx == 2:
                    thrd_imgs.append(img_arr)

        with gr.Blocks() as demo:

        #     fst_imgs, snd_imgs, thrd_imgs, locations, prices = [], [], [], [], [] # init list for ratings = []
        # is_news = []
        # sizes = []
        # condition_strings = []
        # condition_ratings = []
        # is_bikes = []
        # brands = []
        # seller_names = []
        # seller_ratings = []
        # locations = []
        # descriptions = []
        # shortened_descriptions = []
            fst_img_blocks, snd_img_blocks, thrd_img_blocks, location_blocks, price_blocks = [], [], [], [], [] # add rating_blocks
            is_new_blocks = []
            size_blocks = []
            condition_blocks = []
            condition_rating_blocks = []
            is_bike_blocks = []
            brand_blocks = []
            seller_name_blocks = []
            seller_rating_blocks = []
            description_blocks = []
            description_shortened_blocks = []
            for fst_img, snd_img, thrd_img, location, price, is_new, size, condition, condition_rating, is_bike, brand, seller_name, seller_rating, location, description, description_shortened in zip(fst_imgs, snd_imgs, thrd_imgs, locations, prices, is_news, sizes, condition_strings, condition_ratings, is_bikes, brands, seller_names, seller_ratings, locations, descriptions, shortened_descriptions): # iterate over ratings as well
                with gr.Row(equal_height=True):
                    with gr.Column():
                        fst_img_blocks.append(gr.Image(value=fst_img))
                    with gr.Column():
                        snd_img_blocks.append(gr.Image(value=snd_img))
                    with gr.Column():
                        thrd_img_blocks.append(gr.Image(value=thrd_img))
                with gr.Row():
                    with gr.Column():
                        location_blocks.append(gr.Textbox(value=location, info="Location"))
                    with gr.Column():
                        price_blocks.append(gr.Textbox(value=price, info="Price"))
                    with gr.Column():
                        is_new_blocks.append(gr.Textbox(value=is_new, info = "Is new"))
                    with gr.Column():
                        size_blocks.append(gr.Textbox(value=size, info = "Size"))
                    with gr.Column():
                        condition_blocks.append(gr.Textbox(value=condition, info = "Condition"))
                    with gr.Column():
                        condition_rating_blocks.append(gr.Textbox(value=condition_rating, info = "Condition Rating"))
                    with gr.Column():
                        is_bike_blocks.append(gr.Textbox(value=is_bike, info = "Is bike"))
                    with gr.Column():
                        brand_blocks.append(gr.Textbox(value=brand, info = "Brand"))
                    with gr.Column():
                        seller_name_blocks.append(gr.Textbox(value=seller_name, info = "Seller name"))
                    with gr.Column():
                        description_blocks.append(gr.Textbox(value=description, info = "Description"))
                    with gr.Column():
                        description_shortened_blocks.append(gr.Textbox(value=description_shortened, info = "Shortened Description"))

                    
                        
                    # Add column for rating_blocks

            plan_str = list(data_record_collection.execution_stats.plan_strs.values())[0]
            gr.Textbox(value=plan_str, info="Query Plan")

        demo.launch()