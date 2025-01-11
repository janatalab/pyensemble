# Serializers for exporting Experiment, Form, Question, and DataFormat objects to JSON
#
# Use Django REST Framework
# https://www.django-rest-framework.org/

# Example use of the Experiment serializer
#     experiment = Experiment.objects.get(pk=1)
#     experiment_serializer = ExperimentSerializer(experiment)
#
# Render the experiment as JSON
#     experiment_json = JSONRenderer().render(experiment_serializer.data)


from rest_framework import serializers
from rest_framework.renderers import JSONRenderer
from pyensemble.models import Experiment, Form, Question, DataFormat

# Define a custom modelserializer
class CustomModelSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['model_class'] = instance.__class__.__name__
        return ret

class DataFormatSerializer(CustomModelSerializer):
    class Meta:
        model = DataFormat
        fields = '__all__'
        
class QuestionSerializer(CustomModelSerializer):
    data_format = DataFormatSerializer(many=False)

    class Meta:
        model = Question
        fields = '__all__'

class FormSerializer(CustomModelSerializer):
    questions = QuestionSerializer(many=True)

    class Meta:
        model = Form
        # fields = '__all__'
        exclude = ['id','experiments']

class ExperimentSerializer(CustomModelSerializer):
    forms = FormSerializer(many=True)

    class Meta:
        model = Experiment
        # fields = '__all__'
        exclude = ['id']



# Create a method to use the Experiment serializer
#     experiment = Experiment.objects.get(pk=1)
#     experiment_serializer = ExperimentSerializer(experiment)
#
# Render the experiment as JSON
#     experiment_json = JSONRenderer().render(experiment_serializer.data)


