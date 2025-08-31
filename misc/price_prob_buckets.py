import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, date
from typing import Dict, List, Tuple, Optional
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

class PriceProbabilityBuckets:
    def __init__(self, 
                 symbol: str = "NSE:NIFTY 50", # "NSE:NIFTY50-INDEX" - for fyers, # "NSE:NIFTY 50" - for zerodha
                 time_frame: str = "3m", # This interval would need to be supported by the broker
                 start_date: str = "2023-01-01",
                 end_date: str = "2025-08-25",
                 hour_start: int = 9,
                 minute_start: int = 15,
                 hour_end: int = 11,
                 minute_end: int = 30,
                 check_end_hour: int = 14,
                 check_end_minute: int = 30,
                 match_tolerance: float = 0.01,
                 bucket_width: int = 10,
                 top_n_buckets: int = 20):
        """
        Initialize the price probability buckets model with parameters.
        
        Args:
            symbol: Trading symbol to analyze
            time_frame: Time frame for data (e.g., "3m", "5m")
            start_date: Start date for historical data
            end_date: End date for historical data
            hour_start: Start hour for analysis window
            minute_start: Start minute for analysis window
            hour_end: End hour for analysis window
            minute_end: End minute for analysis window
            check_end_hour: Hour to check final price
            check_end_minute: Minute to check final price
            match_tolerance: Tolerance for matching price changes
            bucket_width: Width of price buckets in points
            top_n_buckets: Number of top buckets to consider for prediction
        """
        self.symbol = symbol
        self.time_frame = time_frame
        self.start_date = start_date
        self.end_date = end_date
        self.hour_start = hour_start
        self.minute_start = minute_start
        self.hour_end = hour_end
        self.minute_end = minute_end
        self.check_end_hour = check_end_hour
        self.check_end_minute = check_end_minute
        self.match_tolerance = match_tolerance
        self.bucket_width = bucket_width
        self.top_n_buckets = top_n_buckets
        
        # Data storage
        self.history_data = None
        self.broker = None
        
    def load_data(self, broker_gateway=None):
        """
        Load historical data from broker or use provided data.
        
        Args:
            broker_gateway: Optional broker gateway instance
        """
        if broker_gateway is None:
            from brokers import BrokerGateway
            self.broker = BrokerGateway.from_name("zerodha")
        else:
            self.broker = broker_gateway
            
        # Load historical data
        history = self.broker.get_history(
            self.symbol, 
            self.time_frame, 
            self.start_date, 
            self.end_date
        )
        
        self.history_data = pd.DataFrame(history)
        self.history_data['ts'] = pd.to_datetime(self.history_data['ts'], unit='s').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        self.history_data['hour'] = self.history_data['ts'].dt.hour
        self.history_data['minute'] = self.history_data['ts'].dt.minute
        self.history_data['date'] = self.history_data['ts'].dt.date

    def load_data_for_date(self, date: date):
        """
        Load historical data for a specific date.
        """
        if self.broker is None:
            from brokers import BrokerGateway
            self.broker = BrokerGateway.from_name("fyers")
            
        # Load historical data
        history = self.broker.get_history(
            self.symbol, 
            self.time_frame, 
            date.strftime("%Y-%m-%d"), 
            date.strftime("%Y-%m-%d")
        )
        
        self.history_data_for_date = pd.DataFrame(history)
        self.history_data_for_date['ts'] = pd.to_datetime(self.history_data_for_date['ts'], unit='s').dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        self.history_data_for_date['hour'] = self.history_data_for_date['ts'].dt.hour
        self.history_data_for_date['minute'] = self.history_data_for_date['ts'].dt.minute
        self.history_data_for_date['date'] = self.history_data_for_date['ts'].dt.date
        return self.history_data_for_date
    
    def process_daily_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Process historical data to extract opening prices and last 15 minutes averages for each day.
        
        Args:
            data: DataFrame with columns ['ts', 'open', 'close', 'date', 'hour', 'minute']
        
        Returns:
            DataFrame with columns ['date', 'opening_price', 'last_15min_avg']
        """
        # Get opening price for each day (first record of the day)
        daily_openings = data.groupby('date').first()[['open']].reset_index()
        daily_openings.columns = ['date', 'opening_price']
        
        # Process each day to get the last 15 minutes of available data
        last_15min_averages = []
        
        for date in data['date'].unique():
            day_data = data[data['date'] == date].sort_values('ts')
            
            if len(day_data) >= 15:
                # Get the last 15 records (minutes) for this day
                last_15_records = day_data.tail(15)
            else:
                # If less than 15 records available, use all available records
                last_15_records = day_data
            
            # Calculate (open + close) / 2 for each minute in the last 15 minutes
            last_15_records['avg_price'] = (last_15_records['open'] + last_15_records['close']) / 2
            
            # Calculate average of the last 15 minutes for this day
            last_15min_avg = last_15_records['avg_price'].mean()
            
            last_15min_averages.append({
                'date': date,
                'last_15min_avg': last_15min_avg
            })
        
        # Create DataFrame from last 15 minutes averages
        daily_last_15min_avg = pd.DataFrame(last_15min_averages)
        
        # Merge opening prices with last 15 minutes averages
        result = pd.merge(daily_openings, daily_last_15min_avg, on='date', how='left')
        
        # Round to 2 decimal places
        result['opening_price'] = result['opening_price'].round(2)
        result['last_15min_avg'] = result['last_15min_avg'].round(2)
        
        return result
    
    def create_points_from_open_buckets(self, data: pd.DataFrame, current_open_price: float = None) -> Tuple[pd.DataFrame, int]:
        """
        Create buckets based on points difference from opening price.
        Ensures buckets cover a wide range to avoid None values.
        
        Args:
            data: DataFrame with 'close' and 'open' columns
            current_open_price: Current day's opening price for reference
        
        Returns:
            Tuple of (bucket_summary, bucket_width)
        """
        # Calculate points difference from open
        data['points_from_open'] = (data['close'] - data['open']).round(2)
        
        # Create comprehensive bucket range from -500 to +500 points
        # This ensures we capture all possible price movements
        start_point = -500
        end_point = 500
        
        bucket_boundaries = []
        current_point = start_point
        while current_point <= end_point:
            bucket_boundaries.append(current_point)
            current_point += self.bucket_width
        
        # Create bucket labels
        bucket_labels = []
        for i in range(len(bucket_boundaries) - 1):
            bucket_labels.append(f"{bucket_boundaries[i]:.0f}-{bucket_boundaries[i+1]:.0f}")
        
        # Assign each points difference to a bucket
        data['bucket'] = pd.cut(data['points_from_open'], bins=bucket_boundaries, labels=bucket_labels, include_lowest=True)
        
        # Calculate frequency for each bucket
        bucket_freq = data['bucket'].value_counts().sort_index()
        
        # Create bucket summary DataFrame
        bucket_summary = pd.DataFrame({
            'points_range': bucket_freq.index,
            'frequency': bucket_freq.values,
            'bucket_center': [(bucket_boundaries[i] + bucket_boundaries[i+1]) / 2 for i in range(len(bucket_boundaries) - 1)]
        })
        
        return bucket_summary, self.bucket_width
    
    def predict_for_date(self, target_date: date) -> Dict:
        """
        Make prediction for a specific date using only historical data before that date.
        
        Args:
            target_date: Date to predict for
            
        Returns:
            Dictionary containing prediction results
        """
        if self.history_data is None:
            raise ValueError("Data not loaded. Call load_data() first.")
        
        # Split data into historical and current
        current_date_data = self.history_data[self.history_data['ts'].dt.date == target_date]
        historical_data = self.history_data[self.history_data['ts'].dt.date < target_date]
        
        if len(current_date_data) == 0:
            try:
                current_date_data = self.load_data_for_date(target_date)
            except Exception as e:
                return {
                    'date': target_date,
                    'status': 'no_data',
                    'error': f'No data available for {target_date}'
                }
        
        # Filter data for analysis window
        till_now_data = current_date_data[
            (current_date_data['hour'] >= self.hour_start) &
            (current_date_data['hour'] <= self.hour_end) &
            (current_date_data['minute'] >= self.minute_start) &
            (current_date_data['minute'] <= self.minute_end)
        ]
        
        historical_data_filtered = historical_data[
            (historical_data['hour'] >= self.hour_start) &
            (historical_data['hour'] <= self.hour_end) &
            (historical_data['minute'] >= self.minute_start) &
            (historical_data['minute'] <= self.minute_end)
        ]
        
        if len(till_now_data) == 0 or len(historical_data_filtered) == 0:
            return {
                'date': target_date,
                'status': 'insufficient_data',
                'error': 'Insufficient data for analysis window'
            }
        
        # Process data
        till_now_data_calculated = self.process_daily_data(till_now_data)
        historical_data_filtered_calculated = self.process_daily_data(historical_data_filtered)
        
        # Calculate price change till now
        price_change_till_now = ((till_now_data_calculated['last_15min_avg'].iloc[-1] - 
                                 till_now_data_calculated['opening_price'].iloc[0]) * 100 / 
                                till_now_data_calculated['opening_price'].iloc[0]).round(2)
        
        # Calculate historical price changes
        historical_data_filtered_summary = historical_data_filtered_calculated.sort_values('date', ascending=True)
        historical_data_filtered_summary['price_change'] = (
            (historical_data_filtered_summary['last_15min_avg'] - historical_data_filtered_summary['opening_price']) * 100 / 
            historical_data_filtered_summary['opening_price']
        ).round(2)
        
        # Find matching dates
        temp = historical_data_filtered_summary[
            (historical_data_filtered_summary['price_change'] <= price_change_till_now + self.match_tolerance) &
            (historical_data_filtered_summary['price_change'] >= price_change_till_now - self.match_tolerance)
        ]
        matching_dates = temp['date'].tolist()
        
        if len(matching_dates) == 0:
            return {
                'date': target_date,
                'status': 'no_matches',
                'error': 'No matching historical patterns found',
                'price_change_till_now': price_change_till_now
            }
        
        # Get data for matching dates at check_end time
        req_data = historical_data[historical_data['date'].isin(matching_dates)]
        req_data = req_data[
            (req_data['hour'] >= self.hour_end) &
            (req_data['hour'] <= self.minute_end) &
            (req_data['minute'] >= self.check_end_hour) &
            (req_data['minute'] <= self.check_end_minute)
        ]
        
        if len(req_data) == 0:
            return {
                'date': target_date,
                'status': 'no_end_data',
                'error': 'No data available at check_end time for matching dates',
                'matching_dates_count': len(matching_dates)
            }
        
        # Create histogram table
        req_data_calculated = req_data.groupby('date', as_index=False).agg({'close': 'last', 'open': 'first'})
        
        histogram_data = []
        for date in req_data_calculated['date']:
            histogram_data.append({
                'date': date,
                'open': req_data_calculated[req_data_calculated['date'] == date]['open'].iloc[0],
                'close': req_data_calculated[req_data_calculated['date'] == date]['close'].iloc[0],
            })
        
        histogram_table = pd.DataFrame(histogram_data)
        
        # Get actual opening price for today first
        actual_open_today = current_date_data['open'].iloc[0]  # Opening price for today
        
        # Create buckets with current opening price reference
        bucket_summary, _ = self.create_points_from_open_buckets(histogram_table, actual_open_today)
        
        # Get top N buckets
        top_buckets = bucket_summary.nlargest(self.top_n_buckets, 'frequency')
        total_days = historical_data['date'].nunique() # len(histogram_table)
        top_buckets['probability'] = (top_buckets['frequency'] / len(matching_dates) * 100).round(2)
        
        # Calculate predicted change (weighted average of top buckets)
        # predicted_points = 0
        # total_weight = 0
        # for _, bucket in top_buckets.iterrows():
        #     bucket_center = bucket['bucket_center']
        #     weight = bucket['frequency']
        #     predicted_points += bucket_center * weight
        #     total_weight += weight
        
        # predicted_points_from_open = predicted_points / total_weight if total_weight > 0 else 0
        predicted_points_from_open = None
        # Get actual result
        actual_end_data = current_date_data[
            (current_date_data['hour'] == self.check_end_hour) & 
            (current_date_data['minute'] == self.check_end_minute)
        ]
        
        if len(actual_end_data) == 0:
            return {
                'date': target_date,
                'status': 'no_actual_data',
                'error': f'No actual data available for {self.check_end_hour}:{self.check_end_minute:02d}',
                'predictions': top_buckets.to_dict('records'),
                'matching_dates_count': len(matching_dates),
                'predicted_points_from_open': predicted_points_from_open
            }
        
        actual_close_at_end = actual_end_data['close'].iloc[0]
        actual_points_from_open = actual_close_at_end - actual_open_today
        
        # Find actual bucket
        actual_bucket = None
        actual_bucket_ranking = None
        prediction_success = False
        
        for _, row in bucket_summary.iterrows():
            bucket_range = str(row['points_range'])
            if '-' in bucket_range and bucket_range.strip():
                try:
                    parts = bucket_range.split('-')
                    if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                        start = float(parts[0].strip())
                        end = float(parts[1].strip())
                        if start <= actual_points_from_open <= end:
                            actual_bucket = bucket_range
                            break
                except (ValueError, IndexError):
                    continue
        
        if actual_bucket:
            bucket_frequency = bucket_summary[bucket_summary['points_range'] == actual_bucket]['frequency'].iloc[0]
            bucket_probability = (bucket_frequency / len(matching_dates) * 100).round(2)
            actual_bucket_ranking = bucket_summary[bucket_summary['frequency'] >= bucket_frequency].shape[0]
            prediction_success = None # actual_bucket in top_buckets['points_range'].values
        
        # Calculate prediction accuracy metrics
        # prediction_error = abs(actual_points_from_open - predicted_points_from_open)
        # prediction_error_percentage = (prediction_error / abs(actual_points_from_open)) * 100 if actual_points_from_open != 0 else 0
        
        # Calculate directionality metrics
        # actual_direction = 1 if actual_points_from_open > 0 else (-1 if actual_points_from_open < 0 else 0)
        # predicted_direction = 1 if predicted_points_from_open > 0 else (-1 if predicted_points_from_open < 0 else 0)
        # direction_match = actual_direction == predicted_direction
        
        return {
            'date': target_date,
            'status': 'success',
            'price_change_till_now': price_change_till_now,
            'matching_dates_count': len(matching_dates),
            'total_historical_days': total_days,
            'predictions': top_buckets.to_dict('records'),
            'actual_open': actual_open_today,
            'actual_close': actual_close_at_end,
            'actual_points_from_open': actual_points_from_open,
            # 'predicted_points_from_open': predicted_points_from_open,
            # 'prediction_error': prediction_error,
            # 'prediction_error_percentage': prediction_error_percentage,
            # 'actual_direction': actual_direction,
            # 'predicted_direction': predicted_direction,
            # 'direction_match': direction_match,
            'actual_bucket': actual_bucket,
            'actual_bucket_ranking': actual_bucket_ranking,
            # 'prediction_success': prediction_success,
            # 'top_5_coverage': (top_buckets['frequency'].sum() / total_days * 100).round(1)
        }

if __name__ == "__main__":
    model = PriceProbabilityBuckets()
    model.load_data()
    result = model.predict_for_date(date(2025, 8, 25))
    print(result)
    import pandas as pd
    df = pd.DataFrame(result['predictions'])
    print(df)
