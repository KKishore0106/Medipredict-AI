import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import Counter
from statistics import mean
from bson import ObjectId
from itertools import groupby

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_prediction_trends(user_id: str, db_manager, days: int = 30) -> Dict[str, Any]:
    """Calculate prediction trends over time.
    
    Args:
        user_id: User ID to calculate metrics for
        db_manager: DatabaseManager instance
        days: Number of days to analyze
        
    Returns:
        Dict containing prediction trends
    """
    try:
        if not ObjectId.is_valid(user_id):
            raise ValueError(f"Invalid user_id: {user_id}")

        start_date = datetime.now() - timedelta(days=days)
        pipeline = [
            {
                '$match': {
                    'user_id': user_id,
                    'created_at': {'$gte': start_date}
                }
            },
            {
                '$group': {
                    '_id': {
                        'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}},
                        'hour': {'$hour': '$created_at'}
                    },
                    'count': {'$sum': 1},
                    'avg_confidence': {'$avg': '$confidence_score'},
                    'correct': {
                        '$sum': {
                            '$cond': [
                                {'$eq': ['$predicted_result', '$actual_result']},
                                1,
                                0
                            ]
                        }
                    }
                }
            },
            {'$sort': {'_id': 1}}
        ]

        results = list(db_manager.predictions.aggregate(pipeline))
        
        accuracy_by_hour = {}
        for result in results:
            hour = result['_id']
            accuracy = (result['correct'] / result['count']) * 100 if result['count'] > 0 else 0
            accuracy_by_hour[hour] = {
                'accuracy': accuracy,
                'count': result['count']
            }
            
        return accuracy_by_hour

    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        return {}
    except Exception as e:
        logger.error(f"Error calculating time-based accuracy: {e}", exc_info=True)
        return {}

def get_most_predicted_conditions(user_id: str, db_manager, limit: int = 5) -> List[Dict[str, Any]]:
    """Get most frequently predicted conditions.
    
    Args:
        user_id: User ID to calculate metrics for
        db_manager: DatabaseManager instance
        limit: Number of top conditions to return
        
    Returns:
        List of most predicted conditions with counts
    """
    try:
        if not ObjectId.is_valid(user_id):
            raise ValueError(f"Invalid user_id: {user_id}")

        # Get all predictions with disease types
        predictions = list(db_manager.predictions.find({
            'user_id': user_id,
            'disease_type': {'$exists': True}
        }))

        if not predictions:
            return []

        # Calculate disease distribution
        disease_counts = Counter(p['disease_type'] for p in predictions)
        total = len(predictions)
        
        # Get top conditions
        top_conditions = []
        for disease, count in disease_counts.most_common(limit):
            top_conditions.append({
                'disease': disease,
                'count': count,
                'percentage': (count / total) * 100 if total > 0 else 0
            })

        return top_conditions

    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        return []
    except Exception as e:
        logger.error(f"Error calculating most predicted conditions: {e}")
        return []

def calculate_prediction_accuracy(user_id: str, db_manager) -> Dict[str, Any]:
    """Calculate prediction accuracy.
    
    Args:
        user_id: User ID to calculate metrics for
        db_manager: DatabaseManager instance
        
    Returns:
        Dict containing overall accuracy and breakdown by disease type
    """
    try:
        if not ObjectId.is_valid(user_id):
            raise ValueError(f"Invalid user_id: {user_id}")

        # Get all predictions with results
        predictions = list(db_manager.predictions.find({
            'user_id': user_id,
            'actual_result': {'$exists': True}
        }))

        if not predictions:
            return {
                'overall': 0.0,
                'by_disease': {},
                'total_predictions': 0
            }

        # Calculate overall accuracy
        correct = sum(1 for p in predictions 
            if p.get('predicted_result') == p.get('actual_result'))
        
        total = len(predictions)
        overall_accuracy = (correct / total) * 100 if total > 0 else 0.0

        # Calculate accuracy by disease type
        by_disease = {}
        for disease, group in groupby(sorted(predictions, key=lambda x: x.get('disease_type', '')),
                                   key=lambda x: x.get('disease_type', '')):
            group_predictions = list(group)
            correct_disease = sum(1 for p in group_predictions 
                                if p.get('predicted_result') == p.get('actual_result'))
            disease_accuracy = (correct_disease / len(group_predictions)) * 100 if group_predictions else 0.0
            by_disease[disease] = disease_accuracy

        return {
            'overall': overall_accuracy,
            'by_disease': by_disease,
            'total_predictions': total,
            'correct_predictions': correct
        }

    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        return {
            'overall': 0.0,
            'by_disease': {},
            'total_predictions': 0
        }
    except Exception as e:
        logger.error(f"Error calculating prediction accuracy: {e}", exc_info=True)
        return {
            'overall': 0.0,
            'by_disease': {},
            'total_predictions': 0
        }
