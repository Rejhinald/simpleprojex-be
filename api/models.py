from django.db import models
from django.utils import timezone

class Template(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Proposal(models.Model):
    name = models.CharField(max_length=255)
    template = models.ForeignKey(Template, related_name='proposals', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    global_markup_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    def __str__(self):
        return self.name

class ProposalCategory(models.Model):
    name = models.CharField(max_length=255)
    template = models.ForeignKey(Template, related_name='categories', on_delete=models.CASCADE, null=True, blank=True)
    proposal = models.ForeignKey(Proposal, related_name='direct_categories', on_delete=models.CASCADE, null=True, blank=True)
    position = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['position']
    
    def __str__(self):
        return self.name

class ProposalVariable(models.Model):
    VARIABLE_TYPES = (
        ('LINEAR_FEET', 'Linear Feet'),
        ('SQUARE_FEET', 'Square Feet'),
        ('CUBIC_FEET', 'Cubic Feet'),
        ('COUNT', 'Count'),
    )
    
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=VARIABLE_TYPES)
    # Added default_value field with default=0
    default_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    template = models.ForeignKey(Template, related_name='variables', on_delete=models.CASCADE, null=True, blank=True)
    proposal = models.ForeignKey(Proposal, related_name='direct_variables', on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

class ProposalElement(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(ProposalCategory, related_name='elements', on_delete=models.CASCADE, null=True, blank=True)
    material_cost = models.CharField(max_length=255, help_text="Formula or fixed value")
    labor_cost = models.CharField(max_length=255, help_text="Formula or fixed value")
    markup_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    position = models.IntegerField(default=0)
    proposal = models.ForeignKey(Proposal, related_name='direct_elements', on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['position']
    
    def __str__(self):
        return self.name

class ProposalVariableValue(models.Model):
    proposal = models.ForeignKey(Proposal, related_name='variable_values', on_delete=models.CASCADE)
    variable = models.ForeignKey(ProposalVariable, related_name='values', on_delete=models.CASCADE)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ('proposal', 'variable')
    
    def __str__(self):
        return f"{self.variable.name}: {self.value}"

class ProposalElementValue(models.Model):
    proposal = models.ForeignKey(Proposal, related_name='element_values', on_delete=models.CASCADE)
    element = models.ForeignKey(ProposalElement, related_name='values', on_delete=models.CASCADE)
    calculated_material_cost = models.DecimalField(max_digits=10, decimal_places=2)
    calculated_labor_cost = models.DecimalField(max_digits=10, decimal_places=2)
    markup_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ('proposal', 'element')
        
    def __str__(self):
        return f"{self.element.name} for {self.proposal.name}"

class Contract(models.Model):
    # Change from OneToOneField to ForeignKey to allow multiple contracts per proposal
    proposal = models.ForeignKey(Proposal, related_name='contracts', on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)  # Add this field to track the active contract
    version = models.IntegerField(default=1)  # Add version tracking
    client_name = models.CharField(max_length=255)
    client_signature = models.FileField(upload_to='signatures/', null=True, blank=True)
    client_initials = models.CharField(max_length=10, blank=True)
    contractor_name = models.CharField(max_length=255)
    contractor_signature = models.FileField(upload_to='signatures/', null=True, blank=True)
    contractor_initials = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    client_signed_at = models.DateTimeField(null=True, blank=True)
    contractor_signed_at = models.DateTimeField(null=True, blank=True)
    terms_and_conditions = models.TextField()
    
    def __str__(self):
        return f"Contract v{self.version} for {self.proposal.name}"