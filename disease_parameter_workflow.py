# disease_parameter_workflow.py
"""
A workflow manager for disease parameter collection with update, confirm, delete, and predict actions.
"""

from typing import Dict, List, Optional

# Comprehensive disease parameter definitions
DISEASE_PARAMETERS = {
    "diabetes": {
        "pregnancy_count": {
            "description": "Number of times pregnant",
            "range": (0, 20),
            "unit": "times"
        },
        "glucose_level": {
            "description": "Plasma glucose concentration",
            "range": (0, 200),
            "unit": "mg/dL"
        },
        "blood_pressure": {
            "description": "Diastolic blood pressure",
            "range": (0, 150),
            "unit": "mmHg"
        },
        "skin_thickness": {
            "description": "Triceps skin fold thickness",
            "range": (0, 50),
            "unit": "mm"
        },
        "insulin": {
            "description": "2-Hour serum insulin",
            "range": (0, 900),
            "unit": "mu U/ml"
        },
        "bmi": {
            "description": "Body mass index",
            "range": (0, 50),
            "unit": "kg/m²"
        },
        "diabetes_pedigree": {
            "description": "Diabetes pedigree function",
            "range": (0, 2.5),
            "unit": "score"
        },
        "age": {
            "description": "Age of the patient",
            "range": (21, 90),
            "unit": "years"
        }
    },
    "heart": {
        "age": {
            "description": "Age of the patient",
            "range": (29, 77),
            "unit": "years"
        },
        "sex": {
            "description": "Sex of the patient",
            "range": (0, 1),
            "unit": "binary (0=female, 1=male)"
        },
        "chest_pain_type": {
            "description": "Type of chest pain",
            "range": (0, 3),
            "unit": "categorical"
        },
        "resting_blood_pressure": {
            "description": "Resting blood pressure",
            "range": (94, 200),
            "unit": "mmHg"
        },
        "cholesterol": {
            "description": "Serum cholesterol",
            "range": (126, 564),
            "unit": "mg/dL"
        },
        "fasting_blood_sugar": {
            "description": "Fasting blood sugar > 120 mg/dL",
            "range": (0, 1),
            "unit": "binary"
        },
        "resting_ecg": {
            "description": "Resting electrocardiographic results",
            "range": (0, 2),
            "unit": "categorical"
        },
        "max_heart_rate": {
            "description": "Maximum heart rate achieved",
            "range": (71, 202),
            "unit": "bpm"
        },
        "exercise_induced_angina": {
            "description": "Exercise-induced angina",
            "range": (0, 1),
            "unit": "binary"
        },
        "st_depression": {
            "description": "ST depression induced by exercise relative to rest",
            "range": (0, 6.2),
            "unit": "mm"
        },
        "st_slope": {
            "description": "The slope of the peak exercise ST segment",
            "range": (0, 2),
            "unit": "categorical"
        }
    },
    "parkinsons": {
        "mdvp_fo": {
            "description": "Average vocal fundamental frequency",
            "range": (88.45, 260.41),
            "unit": "Hz"
        },
        "mdvp_fhi": {
            "description": "Maximum vocal fundamental frequency",
            "range": (102.15, 592.03),
            "unit": "Hz"
        },
        "mdvp_flo": {
            "description": "Minimum vocal fundamental frequency",
            "range": (65.47, 239.17),
            "unit": "Hz"
        },
        "jitter_percent": {
            "description": "Percent of period-to-period variations",
            "range": (0, 0.1),
            "unit": "%"
        },
        "jitter_abs": {
            "description": "Absolute jitter in microseconds",
            "range": (0, 0.012),
            "unit": "microseconds"
        },
        "shimmer": {
            "description": "Amplitude variations in the voice signal",
            "range": (0.009, 0.2),
            "unit": "dB"
        },
        "nhr": {
            "description": "Noise-to-harmonic ratio",
            "range": (0.001, 0.3),
            "unit": "ratio"
        },
        "rpde": {
            "description": "Recurrence period density entropy",
            "range": (0.1, 0.9),
            "unit": "score"
        },
        "spread1": {
            "description": "Nonlinear dynamical complexity measure",
            "range": (-7.2, 2.0),
            "unit": "score"
        }
    },
    "kidney": {
        "age": {
            "description": "Age of the patient",
            "range": (4, 90),
            "unit": "years"
        },
        "blood_pressure": {
            "description": "Blood pressure",
            "range": (50, 180),
            "unit": "mmHg"
        },
        "specific_gravity": {
            "description": "Specific gravity of urine",
            "range": (1.005, 1.030),
            "unit": "g/mL"
        },
        "albumin": {
            "description": "Albumin levels in urine",
            "range": (0, 5),
            "unit": "scale"
        },
        "sugar": {
            "description": "Sugar levels in urine",
            "range": (0, 5),
            "unit": "scale"
        },
        "red_blood_cells": {
            "description": "Red blood cells in urine",
            "range": (0, 5),
            "unit": "scale"
        },
        "pus_cell": {
            "description": "Pus cells in urine",
            "range": (0, 5),
            "unit": "scale"
        },
        "pus_cell_clumps": {
            "description": "Pus cell clumps in urine",
            "range": (0, 1),
            "unit": "binary"
        }
    },
    "liver": {
        "age": {
            "description": "Age of the patient",
            "range": (4, 90),
            "unit": "years"
        },
        "total_bilirubin": {
            "description": "Total bilirubin",
            "range": (0.4, 75),
            "unit": "mg/dL"
        },
        "direct_bilirubin": {
            "description": "Direct bilirubin",
            "range": (0.1, 19.7),
            "unit": "mg/dL"
        },
        "alkaline_phosphatase": {
            "description": "Alkaline phosphatase",
            "range": (63, 2000),
            "unit": "U/L"
        },
        "alanine_aminotransferase": {
            "description": "Alanine aminotransferase (ALT)",
            "range": (7, 75),
            "unit": "U/L"
        },
        "aspartate_aminotransferase": {
            "description": "Aspartate aminotransferase (AST)",
            "range": (7, 75),
            "unit": "U/L"
        },
        "total_proteins": {
            "description": "Total proteins",
            "range": (4.6, 8.3),
            "unit": "g/dL"
        },
        "albumin": {
            "description": "Albumin",
            "range": (3.4, 5.4),
            "unit": "g/dL"
        }
    },
    "breast_cancer": {
        "radius_mean": {
            "description": "Mean of distances from center to points on the perimeter",
            "range": (6.5, 28),
            "unit": "mm"
        },
        "texture_mean": {
            "description": "Standard deviation of gray-scale values",
            "range": (9.5, 39),
            "unit": "value"
        },
        "perimeter_mean": {
            "description": "Mean size of the breast mass",
            "range": (43, 189),
            "unit": "mm"
        },
        "area_mean": {
            "description": "Mean area of the breast mass",
            "range": (143, 2501),
            "unit": "mm²"
        },
        "smoothness_mean": {
            "description": "Local variation in radius lengths",
            "range": (0.05, 0.16),
            "unit": "score"
        },
        "compactness_mean": {
            "description": "Perimeter² / area - 1.0",
            "range": (0.02, 0.35),
            "unit": "score"
        },
        "concavity_mean": {
            "description": "Severity of concave portions of the contour",
            "range": (0, 0.43),
            "unit": "score"
        }
    }
}



class DiseaseParameterWorkflow:
    def __init__(self, disease_type: str):
        self.disease_type = disease_type.lower()
        self.parameters = DISEASE_PARAMETERS.get(self.disease_type, {})
        self.collected: Dict[str, str] = {}
        self.finished = False

    def get_next_prompt(self) -> Optional[str]:
        for name, meta in self.parameters.items():
            if name not in self.collected:
                desc = meta.get('description', name)
                rng = meta.get('range', None)
                unit = meta.get('unit', '')
                prompt = f"Please provide {desc}"
                if rng:
                    prompt += f" (Range: {rng[0]} to {rng[1]})"
                if unit:
                    prompt += f" [{unit}]"
                prompt += ":"
                return prompt
        return None

    def validate_parameter(self, name: str, value: str):
        meta = self.parameters.get(name)
        if not meta:
            return False, f"Unknown parameter: {name}"
        rng = meta.get('range')
        # Try to cast to float for validation
        try:
            val = float(value)
            if rng and not (rng[0] <= val <= rng[1]):
                return False, f"Value for {name} must be between {rng[0]} and {rng[1]}"
        except ValueError:
            return False, f"Value for {name} must be a number"
        return True, ""

    def collect_parameter(self, name: str, value: str):
        valid, msg = self.validate_parameter(name, value)
        if valid:
            self.collected[name] = value
            return True, ""
        else:
            return False, msg

    def update_parameter(self, name: str, value: str) -> (bool, str):
        if name in self.collected:
            valid, msg = self.validate_parameter(name, value)
            if valid:
                self.collected[name] = value
                return True, ""
            else:
                return False, msg
        return False, f"Parameter {name} not collected yet."

    def delete_parameter(self, name: str) -> bool:
        if name in self.collected:
            del self.collected[name]
            return True
        return False

    def confirm_parameters(self) -> Dict[str, str]:
        return self.collected.copy()

    def is_complete(self) -> bool:
        return all(name in self.collected for name in self.parameters)

    def reset(self):
        self.collected = {}
        self.finished = False

    def to_json(self) -> Dict:
        return {
            'disease_type': self.disease_type,
            'collected': self.collected,
            'pending': [name for name in self.parameters if name not in self.collected],
            'is_complete': self.is_complete(),
            'next_prompt': self.get_next_prompt(),
            'actions': ['update', 'confirm', 'delete', 'predict']
        }

    def handle_user_command(self, command: str, **kwargs):
        cmd = command.lower()
        if cmd == 'update':
            name = kwargs.get('name')
            value = kwargs.get('value')
            if name and value is not None:
                success, msg = self.update_parameter(name, value)
                return {'success': success, 'message': msg or f"Updated {name}."}
            else:
                return {'success': False, 'message': 'Provide both parameter name and new value.'}
        elif cmd == 'delete':
            name = kwargs.get('name')
            if name and self.delete_parameter(name):
                return {'success': True, 'message': f"Deleted {name}."}
            else:
                return {'success': False, 'message': f"Parameter {name} could not be deleted."}
        elif cmd == 'confirm':
            return {'success': True, 'collected': self.confirm_parameters(), 'message': 'Parameters confirmed.'}
        elif cmd == 'predict':
            if self.is_complete():
                return {'success': True, 'collected': self.confirm_parameters(), 'message': 'Ready for prediction.'}
            else:
                return {'success': False, 'message': 'Not all parameters collected.'}
        elif cmd == 'summary':
            return {'success': True, 'state': self.to_json()}
        else:
            return {'success': False, 'message': f"Unknown command: {command}"}

