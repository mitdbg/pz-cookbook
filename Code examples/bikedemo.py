# class Bike:
#     def __init__(self):

import argparse
import json
import os
from pathlib import Path

import gradio as gr
import numpy as np
from PIL import Image

import palimpzest as pz
from palimpzest.utils.udfs import xls_to_tables







FAR_AWAY_ADDRS = [
    "Melcher St",
    "Sleeper St",
    "437 D St",
    "Seaport Blvd",
    "50 Liberty Dr",
    "Telegraph St",
    "Columbia Rd",
    "E 6th St",
    "E 7th St",
    "E 5th St",
]


def within_two_miles_of_mit(record):
    # NOTE: I'm using this hard-coded function so that folks w/out a
    #       Geocoding API key from google can still run this example
    try:
        return not any([street.lower() in record.address.lower() for street in FAR_AWAY_ADDRS]) #one line code, need clarity for it
    except Exception:
        return False


def in_price_range(record):
    try:
        price = record.price
        if isinstance(price, str):
            price = price.strip()
            price = int(price.replace("$", "").replace(",", ""))
        return 6e5 < price <= 2e6
    except Exception:
        return False
    
def is_good_deal(maximum):
    return maximum >= TextBikeListing.price

def is_far ():
    address = TextBikeListing.location
    return address in FAR_AWAY_ADDRS










#Bicycle classes


class BikeListingFiles(pz.Schema):
    """The source text and image data for a real estate listing."""

    listing = pz.StringField(desc="The name of the listing", required=True)
    text_content = pz.StringField(desc="The content of the listing's text description", required=True)
    image_filepaths = pz.ListField(
        element_type=pz.StringField,
        desc="A list of the filepaths for each image of the listing",
        required=True,
    )


class TextBikeListing(BikeListingFiles):
    """Represents a real estate listing with specific fields extracted from its text."""

    address = pz.StringField(desc="The address of the property")
    price = pz.NumericField(desc="The listed price of the property")

    price = pz.NumericField(desc="The listed price of the property")

    brand = pz.StringField(desc="The brand of the bike")
    is_new = pz.BooleanField(desc="True if bicycle is relatively new and fresh and False if otherwiswe") 
    size = pz.NumericalField (desc="The zie of the bike") #variables that can be determined by images and  text


    seller_name = pz.StringField(desc="The name of the seller")
    seller_id = pz.NumericField(desc="The id of the seller")
    seller_rating = pz.NumericField(desc="The rating of the seller")
    location = pz.StringField(desc="The location of the bike seller")
    description = pz.StringField(desc="The description of the bike")
    description_shortened = pz.StringField(desc="The shortened description of the bike")


class ImageBikeListing(BikeListingFiles):
    """Represents a real estate listing with specific fields extracted from its text and images."""

    is_modern_and_attractive = pz.BooleanField(
        desc="True if the home interior design is modern and attractive and False otherwise"
    )
    has_natural_sunlight = pz.BooleanField(
        desc="True if the home interior has lots of natural sunlight and False otherwise"
    )


    is_bike = pz.BooleanField(desc="True if the images show a bike and False otherwise")



    brand = pz.StringField(desc="The brand of the bike")
    is_new = pz.BooleanField(desc="True if the bike is new, and False otherwise")
    size = pz.NumericalField (desc="The size of the bike") #variables that can be determined by images and  text


    condition = pz.NumericalField (desc="The condition of the bike")
    condition_rating = pz.NumericalField(desc="The condition of the bike quantifiied on a 1-10 scale")
    images = pz.ListField(element_type=pz.StringField, desc="List of Images") #is this neccessary



class BikeListingSource(pz.UserSource): #confirm whether or not its correct
    def __init__(self, dataset_id, listings_dir):
        super().__init__(BikeListingFiles, dataset_id)
        self.listings_dir = listings_dir
        self.listings = sorted(os.listdir(self.listings_dir))

    def __len__(self):
        return len(self.listings)

    def get_size(self):
        return sum(file.stat().st_size for file in Path(self.listings_dir).rglob("*"))

    def get_item(self, idx: int):
        # fetch listing
        listing = self.listings[idx]

        # create data record
        dr = pz.DataRecord(self.schema, source_id=listing)
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
        help="The plan executor to use. One of sequential, pipelined, parallel",
        default="parallel",
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
    policy = pz.MaxQuality()
    if args.policy == "mincost":
        policy = pz.MinCost()
    elif args.policy == "mintime":
        policy = pz.MinTime()
    elif args.policy == "maxquality":
        policy = pz.MaxQuality()
    else:
        print("Policy not supported for this demo")
        exit(1)

    execution_engine = None
    executor = args.executor
    if executor == "sequential":
        execution_engine = pz.NoSentinelSequentialSingleThreadExecution
    elif executor == "pipelined":
        execution_engine = pz.NoSentinelPipelinedSingleThreadExecution
    elif executor == "parallel":
        execution_engine = pz.NoSentinelPipelinedParallelExecution
    else:
        print("Executor not supported for this demo")
        exit(1)

    if os.getenv("OPENAI_API_KEY") is None and os.getenv("TOGETHER_API_KEY") is None:
        print("WARNING: Both OPENAI_API_KEY and TOGETHER_API_KEY are unset")

    # create pz plan
    if workload == "enron":
        # datasetid="enron-eval" for paper evaluation
        plan = pz.Dataset(datasetid, schema=Email)
        plan = plan.filter(
            "The email is not quoting from a news article or an article written by someone outside of Enron"
        )
        plan = plan.filter(
            'The email refers to a fraudulent scheme (i.e., "Raptor", "Deathstar", "Chewco", and/or "Fat Boy")'
        )

    elif workload == "real-estate":
        # datasetid="real-estate-eval-100" for paper evaluation
        data_filepath = f"testdata/{datasetid}"
        user_dataset_id = f"{datasetid}-user"
        pz.DataDirectory().register_user_source(
            src=RealEstateListingSource(user_dataset_id, data_filepath),
            dataset_id=user_dataset_id,
        )
        plan = pz.Dataset(user_dataset_id, schema=RealEstateListingFiles)
        plan = plan.convert(TextRealEstateListing, depends_on="text_content")
        plan = plan.convert(ImageRealEstateListing, image_conversion=True, depends_on="image_filepaths")
        plan = plan.filter(
            "The interior is modern and attractive, and has lots of natural sunlight",
            depends_on=["is_modern_and_attractive", "has_natural_sunlight"],
        )
        plan = plan.filter(within_two_miles_of_mit, depends_on="address")
        plan = plan.filter(in_price_range, depends_on="price")

    elif workload == "medical-schema-matching":
        # datasetid="biofabric-medium" for paper evaluation
        plan = pz.Dataset(datasetid, schema=pz.XLSFile)
        plan = plan.convert(pz.Table, udf=xls_to_tables, cardinality=pz.Cardinality.ONE_TO_MANY)
        plan = plan.filter("The rows of the table contain the patient age")
        plan = plan.convert(CaseData, desc="The patient data in the table", cardinality=pz.Cardinality.ONE_TO_MANY)

    # execute pz plan
    records, execution_stats = pz.Execute(
        plan,
        policy,
        nocache=True,
        optimization_strategy=pz.OptimizationStrategy.PARETO,
        execution_engine=execution_engine,
        verbose=verbose,
    )

    # save statistics
    if profile:
        stats_path = f"profiling-data/{workload}-profiling.json"
        execution_stats_dict = execution_stats.to_json()
        with open(stats_path, "w") as f:
            json.dump(execution_stats_dict, f)

    # visualize output in Gradio
    if visualize:
        from palimpzest.utils.demo_helpers import print_table

        plan_str = list(execution_stats.plan_strs.values())[-1]
        if workload == "enron":
            print_table(records, cols=["sender", "subject"], plan_str=plan_str)

        elif workload == "real-estate":
            fst_imgs, snd_imgs, thrd_imgs, addrs, prices = [], [], [], [], []
            for record in records:
                addrs.append(record.address)
                prices.append(record.price)
                for idx, img_name in enumerate(["img1.png", "img2.png", "img3.png"]):
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
                fst_img_blocks, snd_img_blocks, thrd_img_blocks, addr_blocks, price_blocks = [], [], [], [], []
                for fst_img, snd_img, thrd_img, addr, price in zip(fst_imgs, snd_imgs, thrd_imgs, addrs, prices):
                    with gr.Row(equal_height=True):
                        with gr.Column():
                            fst_img_blocks.append(gr.Image(value=fst_img))
                        with gr.Column():
                            snd_img_blocks.append(gr.Image(value=snd_img))
                        with gr.Column():
                            thrd_img_blocks.append(gr.Image(value=thrd_img))
                    with gr.Row():
                        with gr.Column():
                            addr_blocks.append(gr.Textbox(value=addr, info="Address"))
                        with gr.Column():
                            price_blocks.append(gr.Textbox(value=price, info="Price"))

                plan_str = list(execution_stats.plan_strs.values())[0]
                gr.Textbox(value=plan_str, info="Query Plan")

            demo.launch()