import json
import logging
import os
from datetime import datetime
from logger import logger


class OrderTracker:
    """
    Manages placing, tracking, and persisting orders.
    Stores all orders in a dictionary with order_id as key.
    Keeps track of the current active order.
    Data is saved to and loaded from a JSON file.
    """
    def __init__(self, orders_file='artifacts/orders_data.json'):
        self.orders_file = orders_file
        self._all_orders = {}       
        self._order_ids_not_completed = []
        self._current_order = None  # Private attribute for the most recent order
        # self._load_orders()         # Load orders when the manager is initialized
        self._order_ids_completed = []
        self._order_types_summary = {}

    def _load_orders(self):
        """
        Loads all orders from the JSON file into the _all_orders dictionary.
        This is a private helper method.
        """
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.orders_file), exist_ok=True)

        if os.path.exists(self.orders_file) and os.path.getsize(self.orders_file) > 0:
            try:
                with open(self.orders_file, 'r') as f:
                    # Load directly into the dictionary
                    self._all_orders = json.load(f)
                logger.info(f"Loaded {len(self._all_orders)} orders from '{self.orders_file}'.")

                # Set current_order to the last loaded order if any exist
                # This requires iterating through keys, or having a separate mechanism
                # A simple way is to find the order with the latest timestamp.
                if self._all_orders:
                    # Find the order with the latest timestamp
                    latest_order = None
                    latest_timestamp = None
                    for order_id, order_details in self._all_orders.items():
                        if 'timestamp' in order_details:
                            current_ts = datetime.fromisoformat(order_details['timestamp'])
                            if latest_timestamp is None or current_ts > latest_timestamp:
                                latest_timestamp = current_ts
                                latest_order = order_details
                    self._current_order = latest_order
                    if self._current_order:
                        logger.info(f"Current order set to: {self._current_order['order_id']}")
                    else:
                        logger.info("No valid current order found among loaded orders.")
            except json.JSONDecodeError:
                logger.error(f"Error decoding JSON from '{self.orders_file}'. Starting with empty orders.")
                self._all_orders = {}
                self._current_order = None
            except Exception as e:
                logger.error(f"An unexpected error occurred while loading orders: {e}")
                self._all_orders = {}
                self._current_order = None
        else:
            logger.info(f"No existing order file found at '{self.orders_file}'. Starting fresh.")
            self._all_orders = {}
            self._current_order = None

    def _save_orders(self):
        """
        Saves all orders from the _all_orders dictionary to the JSON file.
        This is a private helper method.
        """
        try:
            # Ensure the directory exists before saving
            os.makedirs(os.path.dirname(self.orders_file), exist_ok=True)
            with open(self.orders_file, 'w') as f:
                json.dump(self._all_orders, f, indent=4) # indent for pretty printing
            logger.info(f"Saved {len(self._all_orders)} orders to '{self.orders_file}'.")
        except IOError as e:
            logger.error(f"Error saving orders to '{self.orders_file}': {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while saving orders: {e}")

    def add_order(self, order_details: dict):
        """
        Adds a new order.
        Args:
            order_details (dict): A dictionary containing the details of the order.
                                  It MUST include a unique 'order_id'.
        """
        order_id = order_details.get('order_id', order_details.get('orders', {}).get('id', None))
        if not order_id:
            logger.error("Cannot place order: 'order_id' is missing from order_details.")
            return

        # Ensure 'timestamp' is present and formatted consistently
        if 'timestamp' not in order_details:
            order_details['timestamp'] = datetime.now().isoformat()

        # Update the current order
        self._current_order = order_details
        logger.debug(f"Order being placed: {self._current_order}")

        # Add or update in the dictionary
        if order_id in self._all_orders:
            logger.warning(f"Order with ID '{order_id}' already exists. Updating existing order.")
        self._all_orders[order_id] = self._current_order
        logger.debug(f"Order '{order_id}' added/updated in in-memory dictionary.")

        # Save all orders to disk after each placement
        # self._save_orders()
        # logger.info("Orders saved to disk.")


    @property
    def current_order(self):
        """
        Property to get the most recently placed order.
        """
        return self._current_order

    @property
    def all_orders(self):
        """
        Property to get a copy of all orders placed so far (as a dictionary).
        Returns a copy to prevent external modification of the internal dictionary.
        """
        return self._all_orders.copy() # Return a copy of the dictionary

    @property
    def completed_order_ids(self):
        """
        Returns a list of completed order IDs.
        """
        return list(self._order_ids_completed)

    @property
    def completed_orders(self):
        """
        Returns a list of completed order details (dicts).
        """
        return [self._all_orders[oid] for oid in self._order_ids_completed if oid in self._all_orders]

    @property
    def non_completed_order_ids(self):
        """
        Returns a list of non-completed order IDs.
        """
        return [oid for oid in self._all_orders if oid not in self._order_ids_completed]

    @property
    def non_completed_orders(self):
        """
        Returns a list of non-completed order details (dicts).
        """
        return [self._all_orders[oid] for oid in self._all_orders if oid not in self._order_ids_completed]

    def get_order_by_id(self, order_id: str):
        """
        Retrieves an order by its order_id (efficient dictionary lookup).
        """
        return self._all_orders.get(order_id) # Use .get() for safe access

    def get_total_orders_count(self):
        """
        Returns the total number of orders managed.
        """
        return len(self._all_orders)

    def get_all_orders_as_list(self):
        """
        Returns all orders as a list of dictionaries (useful for iteration if needed).
        """
        return list(self._all_orders.values())
    
    def complete_order(self, order_id: str):
        """
        Marks an order as completed.
        """
        if order_id in self._all_orders:
            if order_id not in self._order_ids_completed:
                self._order_ids_completed.append(order_id)
                if self._all_orders[order_id]['transaction_type'] not in self._order_types_summary:
                    self._order_types_summary[self._all_orders[order_id]['transaction_type']] = 1
                else:
                    self._order_types_summary[self._all_orders[order_id]['transaction_type']] += 1
                logger.info(f"Order '{order_id}' marked as completed.")
            else:
                logger.info(f"Order '{order_id}' already marked as completed.")
            return True
        else:
            logger.error(f"Order '{order_id}' not found in the order tracker.")
            return False

    def remove_order(self, order_id: str):
        """
        Removes an order from the order tracker.
        """
        if order_id in self._all_orders:
            del self._all_orders[order_id]  
            # self._save_orders()
            logger.info(f"Order '{order_id}' removed from the order tracker.")
            return True
        else:
            logger.error(f"Order '{order_id}' not found in the order tracker.")
            return False

    def _record_order_complete(self, order_id: str, transaction_type: str):
        """
        Records order completion statistics.
        """
        if order_id not in self._order_ids_completed:
            if transaction_type not in self._order_types_summary:
                self._order_types_summary[transaction_type] = 1
            else:
                self._order_types_summary[transaction_type] += 1

    def get_order_summary(self):
        """
        Returns a summary of order statistics.
        """
        return {
            'total_orders': len(self._all_orders),
            'completed_orders': len(self._order_ids_completed),
            'active_orders': len(self._all_orders) - len(self._order_ids_completed),
            'order_types_summary': self._order_types_summary.copy(),
            'current_order': self._current_order
        }

    def print_status(self, additional_info=None):
        """
        Prints current order status and statistics.
        
        Args:
            additional_info (dict): Additional information to display
        """
        summary = self.get_order_summary()
        
        logger.info("="*50)
        logger.info(f"ORDER STATUS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*50)
        logger.info(f"Total Orders: {summary['total_orders']}")
        logger.info(f"Completed Orders: {summary['completed_orders']}")
        logger.info(f"Active Orders: {summary['active_orders']}")
        logger.info(f"Order Types Summary: {summary['order_types_summary']}")
        
        if self._all_orders:
            logger.info(f"Current Orders: {self._all_orders}")
            
        if additional_info:
            logger.info("Additional Info:")
            for key, value in additional_info.items():
                logger.info(f"  {key}: {value}")
                
        logger.info("="*50)