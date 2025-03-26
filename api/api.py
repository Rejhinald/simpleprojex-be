from ninja import NinjaAPI, Schema, ModelSchema, File, Form
from ninja.files import UploadedFile
from ninja.pagination import paginate
from typing import List, Optional, Dict, Any, Union
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.db import transaction
from datetime import datetime
from .models import (
    Template, ProposalCategory, ProposalVariable, ProposalElement,
    Proposal, ProposalVariableValue, ProposalElementValue, Contract
)

api = NinjaAPI(title="Proposal System API")

# ======================
# === Schema Classes ===
# ======================

class TemplateSchema(ModelSchema):
    class Config:
        model = Template
        model_fields = ["id", "name", "description", "created_at"]

class TemplateCreateSchema(Schema):
    name: str
    description: str = ""

class ProposalUpdateSchema(Schema):
    name: Optional[str] = None
    global_markup_percentage: Optional[float] = None

class CategorySchema(ModelSchema):
    class Config:
        model = ProposalCategory
        model_fields = ["id", "name", "position"]

class CategoryCreateSchema(Schema):
    name: str
    position: int = 0

class VariableSchema(ModelSchema):
    class Config:
        model = ProposalVariable
        model_fields = ["id", "name", "type"]

class VariableCreateSchema(Schema):
    name: str
    type: str  # LINEAR_FEET, SQUARE_FEET, CUBIC_FEET, COUNT

class ElementSchema(ModelSchema):
    class Config:
        model = ProposalElement
        model_fields = ["id", "name", "material_cost", "labor_cost", "markup_percentage", "position"]

class ElementCreateSchema(Schema):
    name: str
    material_cost: str
    labor_cost: str
    markup_percentage: float = 0
    position: int = 0

class ProposalSchema(ModelSchema):
    class Config:
        model = Proposal
        model_fields = ["id", "name", "created_at", "global_markup_percentage"]
    
    template_id: Optional[int] = None

class ProposalCreateFromTemplateSchema(Schema):
    name: str
    template_id: int
    global_markup_percentage: float = 0

class ProposalCreateFromScratchSchema(Schema):
    name: str
    global_markup_percentage: float = 0

class VariableValueSchema(Schema):
    variable_id: int
    value: float

class ElementValueSchema(Schema):
    element_id: int
    calculated_material_cost: float
    calculated_labor_cost: float
    markup_percentage: float = 0

class ContractSchema(ModelSchema):
    class Config:
        model = Contract
        model_fields = ["id", "client_name", "client_initials", "contractor_name", 
                        "contractor_initials", "created_at", "client_signed_at", 
                        "contractor_signed_at", "terms_and_conditions"]
    
    proposal_id: int

class ContractCreateSchema(Schema):
    proposal_id: int
    client_name: str
    client_initials: str = ""
    contractor_name: str
    contractor_initials: str = ""
    terms_and_conditions: str

class ContractCreateFromProposalSchema(Schema):
    client_name: str
    client_initials: str = ""
    contractor_name: str
    contractor_initials: str = ""
    terms_and_conditions: str

class SignatureSchema(Schema):
    signature: str = ""  # Base64 encoded string or other text representation
    initials: str = ""

# ======================
# === Template APIs ===
# ======================

@api.get("/templates", response=List[TemplateSchema])
@paginate
def list_templates(request):
    return Template.objects.all()

@api.post("/templates", response=TemplateSchema)
def create_template(request, data: TemplateCreateSchema):
    template = Template.objects.create(**data.dict())
    return template

@api.get("/templates/{template_id}", response=TemplateSchema)
def get_template(request, template_id: int):
    template = get_object_or_404(Template, id=template_id)
    return template

@api.put("/templates/{template_id}", response=TemplateSchema)
def update_template(request, template_id: int, data: TemplateCreateSchema):
    template = get_object_or_404(Template, id=template_id)
    for key, value in data.dict().items():
        setattr(template, key, value)
    template.save()
    return template

@api.delete("/templates/{template_id}")
def delete_template(request, template_id: int):
    template = get_object_or_404(Template, id=template_id)
    template.delete()
    return {"success": True}

# ======================
# === Category APIs ===
# ======================

@api.get("/templates/{template_id}/categories", response=List[CategorySchema])
def list_categories(request, template_id: int):
    template = get_object_or_404(Template, id=template_id)
    return template.categories.all()

@api.post("/templates/{template_id}/categories", response=CategorySchema)
def create_category(request, template_id: int, data: CategoryCreateSchema):
    template = get_object_or_404(Template, id=template_id)
    category = ProposalCategory.objects.create(
        template=template,
        **data.dict()
    )
    return category

@api.put("/categories/{category_id}", response=CategorySchema)
def update_category(request, category_id: int, data: CategoryCreateSchema):
    category = get_object_or_404(ProposalCategory, id=category_id)
    for key, value in data.dict().items():
        setattr(category, key, value)
    category.save()
    return category

@api.delete("/categories/{category_id}")
def delete_category(request, category_id: int):
    category = get_object_or_404(ProposalCategory, id=category_id)
    category.delete()
    return {"success": True}

# ======================
# === Variable APIs ===
# ======================

@api.get("/templates/{template_id}/variables", response=List[VariableSchema])
def list_variables(request, template_id: int):
    template = get_object_or_404(Template, id=template_id)
    return template.variables.all()

@api.post("/templates/{template_id}/variables", response=VariableSchema)
def create_variable(request, template_id: int, data: VariableCreateSchema):
    template = get_object_or_404(Template, id=template_id)
    variable = ProposalVariable.objects.create(
        template=template,
        **data.dict()
    )
    return variable

@api.put("/variables/{variable_id}", response=VariableSchema)
def update_variable(request, variable_id: int, data: VariableCreateSchema):
    variable = get_object_or_404(ProposalVariable, id=variable_id)
    for key, value in data.dict().items():
        setattr(variable, key, value)
    variable.save()
    return variable

@api.delete("/variables/{variable_id}")
def delete_variable(request, variable_id: int):
    variable = get_object_or_404(ProposalVariable, id=variable_id)
    variable.delete()
    return {"success": True}

# ======================
# === Element APIs ===
# ======================

@api.get("/categories/{category_id}/elements", response=List[ElementSchema])
def list_elements(request, category_id: int):
    category = get_object_or_404(ProposalCategory, id=category_id)
    return category.elements.all()

@api.post("/categories/{category_id}/elements", response=ElementSchema)
def create_element(request, category_id: int, data: ElementCreateSchema):
    category = get_object_or_404(ProposalCategory, id=category_id)
    element = ProposalElement.objects.create(
        category=category,
        **data.dict()
    )
    return element

@api.put("/elements/{element_id}", response=ElementSchema)
def update_element(request, element_id: int, data: ElementCreateSchema):
    element = get_object_or_404(ProposalElement, id=element_id)
    for key, value in data.dict().items():
        setattr(element, key, value)
    element.save()
    return element

@api.delete("/elements/{element_id}")
def delete_element(request, element_id: int):
    element = get_object_or_404(ProposalElement, id=element_id)
    element.delete()
    return {"success": True}

# ======================
# === Proposal APIs ===
# ======================

@api.get("/proposals", response=List[ProposalSchema])
@paginate
def list_proposals(request):
    return Proposal.objects.all()

@api.post("/proposals/from-template", response=ProposalSchema)
@transaction.atomic
def create_proposal_from_template(request, data: ProposalCreateFromTemplateSchema):
    template = get_object_or_404(Template, id=data.template_id)
    
    proposal = Proposal.objects.create(
        name=data.name,
        template=template,
        global_markup_percentage=data.global_markup_percentage
    )
    
    # Clone elements and calculate initial values
    for category in template.categories.all():
        for element in category.elements.all():
            ProposalElementValue.objects.create(
                proposal=proposal,
                element=element,
                calculated_material_cost=0,  # Will be calculated when variables are set
                calculated_labor_cost=0,     # Will be calculated when variables are set
                markup_percentage=element.markup_percentage
            )
    
    return proposal

@api.post("/proposals/from-scratch", response=ProposalSchema)
def create_proposal_from_scratch(request, data: ProposalCreateFromScratchSchema):
    proposal = Proposal.objects.create(
        name=data.name,
        global_markup_percentage=data.global_markup_percentage
    )
    return proposal

@api.get("/proposals/{proposal_id}", response=ProposalSchema)
def get_proposal(request, proposal_id: int):
    proposal = get_object_or_404(Proposal, id=proposal_id)
    return proposal

@api.put("/proposals/{proposal_id}", response=ProposalSchema)
def update_proposal(request, proposal_id: int, data: ProposalUpdateSchema):
    proposal = get_object_or_404(Proposal, id=proposal_id)
    
    if data.name is not None:
        proposal.name = data.name
        
    if data.global_markup_percentage is not None:
        proposal.global_markup_percentage = data.global_markup_percentage
        
    proposal.save()
    return proposal

@api.delete("/proposals/{proposal_id}")
def delete_proposal(request, proposal_id: int):
    proposal = get_object_or_404(Proposal, id=proposal_id)
    proposal.delete()
    return {"success": True}

# ===========================
# === Variable Value APIs ===
# ===========================

@api.post("/proposals/{proposal_id}/variable-values")
def set_variable_values(request, proposal_id: int, data: List[VariableValueSchema]):
    proposal = get_object_or_404(Proposal, id=proposal_id)
    
    with transaction.atomic():
        for item in data:
            variable = get_object_or_404(ProposalVariable, id=item.variable_id)
            
            # Create or update the variable value
            obj, created = ProposalVariableValue.objects.update_or_create(
                proposal=proposal,
                variable=variable,
                defaults={"value": item.value}
            )
    
    # Here you would typically recalculate the element costs based on variables
    # This would require a formula parser implementation
    
    return {"success": True}

@api.get("/proposals/{proposal_id}/variable-values")
def get_variable_values(request, proposal_id: int):
    proposal = get_object_or_404(Proposal, id=proposal_id)
    values = ProposalVariableValue.objects.filter(proposal=proposal).select_related('variable')
    
    result = []
    for value in values:
        result.append({
            "variable_id": value.variable.id,
            "variable_name": value.variable.name,
            "variable_type": value.variable.type,
            "value": value.value
        })
    
    return result

# ===========================
# === Element Value APIs ===
# ===========================

@api.post("/proposals/{proposal_id}/element-values")
def update_element_values(request, proposal_id: int, data: List[ElementValueSchema]):
    proposal = get_object_or_404(Proposal, id=proposal_id)
    
    with transaction.atomic():
        for item in data:
            element = get_object_or_404(ProposalElement, id=item.element_id)
            
            # Create or update the element value
            obj, created = ProposalElementValue.objects.update_or_create(
                proposal=proposal,
                element=element,
                defaults={
                    "calculated_material_cost": item.calculated_material_cost,
                    "calculated_labor_cost": item.calculated_labor_cost,
                    "markup_percentage": item.markup_percentage
                }
            )
    
    return {"success": True}

@api.get("/proposals/{proposal_id}/element-values")
def get_element_values(request, proposal_id: int):
    proposal = get_object_or_404(Proposal, id=proposal_id)
    values = ProposalElementValue.objects.filter(proposal=proposal).select_related('element')
    
    result = []
    for value in values:
        result.append({
            "element_id": value.element.id,
            "element_name": value.element.name,
            "category_id": value.element.category.id,
            "category_name": value.element.category.name,
            "calculated_material_cost": value.calculated_material_cost,
            "calculated_labor_cost": value.calculated_labor_cost,
            "markup_percentage": value.markup_percentage,
            "total_cost": float(value.calculated_material_cost) + float(value.calculated_labor_cost),
            "total_with_markup": (float(value.calculated_material_cost) + float(value.calculated_labor_cost)) * 
                                (1 + float(value.markup_percentage) / 100)
        })
    
    return result

# ======================
# === Contract APIs ===
# ======================

@api.get("/contracts", response=List[ContractSchema])
@paginate
def list_contracts(request):
    return Contract.objects.all()

@api.post("/proposals/{proposal_id}/generate-contract", response=ContractSchema)
def generate_contract(request, proposal_id: int, data: ContractCreateFromProposalSchema):
    proposal = get_object_or_404(Proposal, id=proposal_id)
    
    # Check if contract already exists
    if hasattr(proposal, 'contract'):
        return {"error": "Contract already exists for this proposal"}, 400
    
    contract = Contract.objects.create(
        proposal=proposal,
        client_name=data.client_name,
        client_initials=data.client_initials,
        contractor_name=data.contractor_name,
        contractor_initials=data.contractor_initials,
        terms_and_conditions=data.terms_and_conditions
    )
    
    return contract

@api.get("/contracts/{contract_id}", response=ContractSchema)
def get_contract(request, contract_id: int):
    contract = get_object_or_404(Contract, id=contract_id)
    return contract

@api.put("/contracts/{contract_id}/client-sign", response=ContractSchema)
def client_sign_contract(request, contract_id: int, data: SignatureSchema):
    contract = get_object_or_404(Contract, id=contract_id)
    
    if data.signature:
        contract.client_signature = data.signature
    if data.initials:
        contract.client_initials = data.initials
    
    contract.client_signed_at = datetime.now()
    contract.save()
    
    return contract

@api.put("/contracts/{contract_id}/contractor-sign", response=ContractSchema)
def contractor_sign_contract(request, contract_id: int, data: SignatureSchema = None):
    contract = get_object_or_404(Contract, id=contract_id)
    
    if data and data.initials:
        contract.contractor_initials = data.initials
    
    contract.contractor_signed_at = datetime.now()
    contract.save()
    
    return contract