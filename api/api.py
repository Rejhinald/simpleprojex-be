from ninja import NinjaAPI, Schema, ModelSchema, File, Form
from ninja.files import UploadedFile
from ninja.pagination import paginate
from typing import List, Optional, Dict, Any, Union
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.db import transaction
from datetime import datetime
from django.http import JsonResponse
import time
from django.db import transaction, OperationalError
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from pathlib import Path
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
        model_fields = ["id", "name", "type", "default_value"]  # Added default_value

class VariableCreateSchema(Schema):
    name: str
    type: str  # LINEAR_FEET, SQUARE_FEET, CUBIC_FEET, COUNT
    default_value: float = 0  # Added default_value with default=0

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
    variable_name: Optional[str] = None
    variable_type: Optional[str] = None
    value: float

# Update the ElementValueSchema to include position fields
class ElementValueSchema(Schema):
    element_id: int
    element_name: Optional[str] = None
    category_name: Optional[str] = None
    calculated_material_cost: float
    calculated_labor_cost: float
    markup_percentage: float = 0
    position: Optional[int] = None
    category_position: Optional[int] = None

class ContractSchema(ModelSchema):
    class Config:
        model = Contract
        model_fields = ["id", "client_name", "client_initials", "client_signature", "contractor_name", 
                        "contractor_initials", "contractor_signature", "created_at", "client_signed_at", 
                        "contractor_signed_at", "terms_and_conditions", "version", "is_active"]
    
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

class VariableValueResponse(Schema):
    variable_id: int
    variable_name: str
    variable_type: str
    value: float

class ElementValueResponse(Schema):
    element_id: int
    element_name: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    calculated_material_cost: str
    calculated_labor_cost: str
    markup_percentage: str
    total_cost: float
    total_with_markup: float
    position: Optional[int] = None  # Add position field
    category_position: Optional[int] = None  # Add category_position field

# Add new schema for file uploads
class FileUploadSchema(Schema):
    initials: str

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
        name=data.name,
        type=data.type,
        default_value=data.default_value  # Make sure this is included
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
    
    # Create the proposal
    proposal = Proposal.objects.create(
        name=data.name,
        template=template,
        global_markup_percentage=data.global_markup_percentage
    )
    
    print(f"Creating proposal from template: {template.name}")
    
    # Copy variables with their default values
    for variable in template.variables.all():
        print(f"Creating variable value: {variable.name}, default_value={variable.default_value}")
        ProposalVariableValue.objects.create(
            proposal=proposal,
            variable=variable,
            value=variable.default_value  # This should be set correctly now
        )
    
    # Copy categories with their positions
    for category in template.categories.all():
        # Create category for the proposal
        proposal_category = ProposalCategory.objects.create(
            name=category.name,
            template=None,  # This category belongs to the proposal now
            proposal=proposal,
            position=category.position
        )
        
        # Copy elements with their values
        for element in category.elements.all():
            # Create the element for the proposal
            proposal_element = ProposalElement.objects.create(
                name=element.name,
                category=proposal_category,  # Use the new category
                material_cost=element.material_cost,
                labor_cost=element.labor_cost,
                markup_percentage=element.markup_percentage,
                position=element.position,
                proposal=proposal  # Link to proposal
            )
            
            # Create the element value
            # Initialize with the actual material and labor costs from the template
            try:
                material_cost = float(element.material_cost)
            except (ValueError, TypeError):
                material_cost = 0
                
            try:
                labor_cost = float(element.labor_cost)
            except (ValueError, TypeError):
                labor_cost = 0
            
            ProposalElementValue.objects.create(
                proposal=proposal,
                element=proposal_element,
                calculated_material_cost=material_cost,
                calculated_labor_cost=labor_cost,
                markup_percentage=element.markup_percentage
            )
            
            print(f"Created element value for {proposal_element.name} with costs: {material_cost}, {labor_cost}")
    
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
    result = []
    
    try:
        with transaction.atomic():
            for item in data:
                # Handle negative IDs (client-side values)
                if item.variable_id < 0:
                    if not item.variable_name or not item.variable_type:
                        # Proper error response via Django
                        raise ValueError("variable_name and variable_type are required for new variables")
                    
                    # Create a direct variable for this proposal
                    variable = ProposalVariable.objects.create(
                        name=item.variable_name,
                        type=item.variable_type,
                        default_value=item.value,  # Set default value to current value
                        template=None,
                        proposal=proposal  # Direct association
                    )
                    
                    # Create the variable value
                    value = ProposalVariableValue.objects.create(
                        proposal=proposal,
                        variable=variable,
                        value=item.value
                    )
                    
                    result.append({
                        "variable_id": variable.id,
                        "variable_name": variable.name,
                        "variable_type": variable.type,
                        "value": value.value
                    })
                else:
                    # Handle existing variables
                    try:
                        variable = ProposalVariable.objects.get(id=item.variable_id)
                        
                        # Create or update the variable value
                        value, created = ProposalVariableValue.objects.update_or_create(
                            proposal=proposal,
                            variable=variable,
                            defaults={"value": item.value}
                        )
                        
                        result.append({
                            "variable_id": variable.id,
                            "variable_name": variable.name,
                            "variable_type": variable.type,
                            "value": value.value
                        })
                    except ProposalVariable.DoesNotExist:
                        # Proper error handling
                        raise ValueError(f"Variable with ID {item.variable_id} not found")
    except ValueError as e:
        # Return a proper error response for ValueError
        return api.create_response(request, {"detail": str(e)}, status=400)
    except Exception as e:
        # Return a proper error response for other exceptions
        return api.create_response(request, {"detail": str(e)}, status=500)
    
    return result

@api.get("/proposals/{proposal_id}/variable-values", response=List[VariableValueResponse])
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
    result = []
    
    try:
        with transaction.atomic():
            for item in data:
                # Handle negative IDs (client-side values)
                if item.element_id < 0:
                    if not item.element_name:
                        # Proper error response via Django
                        raise ValueError("element_name is required for new elements")
                    
                    # Create or get category if provided
                    category = None
                    if item.category_name:
                        # Try to find existing category
                        categories = ProposalCategory.objects.filter(
                            name=item.category_name,
                            proposal=proposal
                        )
                        
                        if categories.exists():
                            category = categories.first()
                        else:
                            # Create new category with position
                            category_position = item.category_position if hasattr(item, 'category_position') else 0
                            category = ProposalCategory.objects.create(
                                name=item.category_name,
                                template=None,
                                proposal=proposal,
                                position=category_position
                            )
                    
                    # Create a new element with position
                    element_position = item.position if hasattr(item, 'position') else 0
                    element = ProposalElement.objects.create(
                        name=item.element_name,
                        category=category,
                        material_cost="0",  # Fixed value
                        labor_cost="0",     # Fixed value
                        markup_percentage=item.markup_percentage,
                        position=element_position,
                        proposal=proposal  # Direct association
                    )
                    
                    # Create element value
                    value = ProposalElementValue.objects.create(
                        proposal=proposal,
                        element=element,
                        calculated_material_cost=item.calculated_material_cost,
                        calculated_labor_cost=item.calculated_labor_cost,
                        markup_percentage=item.markup_percentage
                    )
                    
                    result.append({
                        "element_id": element.id,
                        "element_name": element.name,
                        "category_name": category.name if category else None,
                        "calculated_material_cost": str(value.calculated_material_cost),
                        "calculated_labor_cost": str(value.calculated_labor_cost),
                        "markup_percentage": str(value.markup_percentage),
                        "position": element.position,
                        "total_cost": float(value.calculated_material_cost) + float(value.calculated_labor_cost),
                        "total_with_markup": (float(value.calculated_material_cost) + float(value.calculated_labor_cost)) * 
                                            (1 + float(value.markup_percentage) / 100)
                    })
                else:
                    # Handle existing elements
                    try:
                        element = ProposalElement.objects.get(id=item.element_id)
                        element_changed = False
                        
                        # Update element name if provided
                        if hasattr(item, 'element_name') and item.element_name:
                            element.name = item.element_name
                            element_changed = True
                        
                        # Update element position if provided
                        if hasattr(item, 'position'):
                            element.position = item.position
                            element_changed = True
                        
                        # Update category if provided
                        if hasattr(item, 'category_name') and item.category_name:
                            # Find or create the category
                            try:
                                category = ProposalCategory.objects.get(
                                    name=item.category_name,
                                    proposal=proposal
                                )
                            except ProposalCategory.DoesNotExist:
                                # Create a new category
                                category_position = getattr(item, 'category_position', 0)
                                category = ProposalCategory.objects.create(
                                    name=item.category_name,
                                    proposal=proposal,
                                    template=None,
                                    position=category_position
                                )
                            
                            # Only update if the category has changed
                            if not element.category or element.category.name != item.category_name:
                                element.category = category
                                element_changed = True
                        
                        # Save element if any field was changed
                        if element_changed:
                            element.save()
                        
                        # Create or update the element value
                        value, created = ProposalElementValue.objects.update_or_create(
                            proposal=proposal,
                            element=element,
                            defaults={
                                "calculated_material_cost": item.calculated_material_cost,
                                "calculated_labor_cost": item.calculated_labor_cost,
                                "markup_percentage": item.markup_percentage
                            }
                        )
                        
                        # Get fresh category info after possible changes
                        current_category = element.category
                        category_name = current_category.name if current_category else None
                        
                        result.append({
                            "element_id": element.id,
                            "element_name": element.name,
                            "category_name": category_name,
                            "calculated_material_cost": str(value.calculated_material_cost),
                            "calculated_labor_cost": str(value.calculated_labor_cost),
                            "markup_percentage": str(value.markup_percentage),
                            "position": element.position,
                            "total_cost": float(value.calculated_material_cost) + float(value.calculated_labor_cost),
                            "total_with_markup": (float(value.calculated_material_cost) + float(value.calculated_labor_cost)) * 
                                                (1 + float(value.markup_percentage) / 100)
                        })
                    except ProposalElement.DoesNotExist:
                        # Proper error handling
                        raise ValueError(f"Element with ID {item.element_id} not found")
    except ValueError as e:
        # Return a proper error response for ValueError
        return api.create_response(request, {"detail": str(e)}, status=400)
    except Exception as e:
        # Return a proper error response for other exceptions
        return api.create_response(request, {"detail": str(e)}, status=500)
    
    return result

@api.get("/proposals/{proposal_id}/element-values", response=List[ElementValueResponse])
def get_element_values(request, proposal_id: int):
    proposal = get_object_or_404(Proposal, id=proposal_id)
    values = ProposalElementValue.objects.filter(proposal=proposal).select_related('element')
    
    result = []
    for value in values:
        try:
            category_id = value.element.category.id if value.element.category else None
            category_name = value.element.category.name if value.element.category else None
            category_position = value.element.category.position if value.element.category else None
            
            result.append({
                "element_id": value.element.id,
                "element_name": value.element.name,
                "category_id": category_id,
                "category_name": category_name,
                "calculated_material_cost": str(value.calculated_material_cost),
                "calculated_labor_cost": str(value.calculated_labor_cost),
                "markup_percentage": str(value.markup_percentage),
                "total_cost": float(value.calculated_material_cost) + float(value.calculated_labor_cost),
                "total_with_markup": (float(value.calculated_material_cost) + float(value.calculated_labor_cost)) * 
                                    (1 + float(value.markup_percentage) / 100),
                "position": value.element.position if hasattr(value.element, 'position') else 0,
                "category_position": category_position
            })
        except Exception as e:
            # Skip any elements that cause errors (like missing relationships)
            continue
    
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
    
    try:
        # Get existing contracts for this proposal
        existing_contracts = Contract.objects.filter(proposal=proposal)
        
        # Set a version number
        version = 1
        if existing_contracts.exists():
            # Set all existing contracts to inactive
            for contract in existing_contracts:
                contract.is_active = False
                contract.save()
            
            # Get the highest version number and increment it
            latest_version = existing_contracts.order_by('-version').first().version
            version = latest_version + 1
        
        # Create new contract
        contract = Contract.objects.create(
            proposal=proposal,
            version=version,
            is_active=True,
            client_name=data.client_name,
            client_initials=data.client_initials,
            contractor_name=data.contractor_name,
            contractor_initials=data.contractor_initials,
            terms_and_conditions=data.terms_and_conditions
        )
        
        return contract
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@api.get("/contracts/{contract_id}", response=ContractSchema)
def get_contract(request, contract_id: int):
    contract = get_object_or_404(Contract, id=contract_id)
    print(f"DEBUG - Contract signature fields: client_signature={contract.client_signature}, contractor_signature={contract.contractor_signature}")
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

@api.post("/proposals/{proposal_id}/sync-template")
def sync_proposal_with_template(request, proposal_id: int):
    proposal = get_object_or_404(Proposal, id=proposal_id)
    
    if not proposal.template:
        return api.create_response(request, {"detail": "This proposal has no associated template"}, status=400)
    
    template = proposal.template
    
    added_variables = []
    updated_variables = []
    added_elements = []
    
    def execute_with_retry(operation_func, max_retries=5, initial_delay=0.1):
        for attempt in range(max_retries):
            try:
                return operation_func()
            except OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    retry_delay = initial_delay * (2 ** attempt)
                    time.sleep(retry_delay)
                    continue
                raise
    
    # Process variables
    with transaction.atomic():
        for template_variable in template.variables.all():
            try:
                # Try to get existing variable value
                variable_value = ProposalVariableValue.objects.filter(
                    proposal=proposal,
                    variable=template_variable
                ).first()
                
                if variable_value:
                    if variable_value.value != template_variable.default_value:
                        variable_value.value = template_variable.default_value
                        variable_value.save()
                        updated_variables.append(template_variable.name)
                else:
                    ProposalVariableValue.objects.create(
                        proposal=proposal,
                        variable=template_variable,
                        value=template_variable.default_value
                    )
                    added_variables.append(template_variable.name)
            except Exception as e:
                print(f"Error processing variable {template_variable.name}: {str(e)}")
    
    # Process categories and elements
    with transaction.atomic():
        for category in template.categories.all():
            # Create or get category for the proposal
            proposal_category, _ = ProposalCategory.objects.get_or_create(
                proposal=proposal,
                name=category.name,
                defaults={
                    'position': category.position,
                    'template': None
                }
            )
            
            # Process elements
            for element in category.elements.all():
                try:
                    # Create or get element
                    proposal_element, _ = ProposalElement.objects.get_or_create(
                        proposal=proposal,
                        name=element.name,
                        category=proposal_category,
                        defaults={
                            'material_cost': element.material_cost,
                            'labor_cost': element.labor_cost,
                            'markup_percentage': element.markup_percentage,
                            'position': element.position
                        }
                    )
                    
                    # Try to get existing element value
                    element_value = ProposalElementValue.objects.filter(
                        proposal=proposal,
                        element=proposal_element
                    ).first()
                    
                    if not element_value:
                        # Create new element value if it doesn't exist
                        try:
                            material_cost = float(element.material_cost)
                        except (ValueError, TypeError):
                            material_cost = 0
                            
                        try:
                            labor_cost = float(element.labor_cost)
                        except (ValueError, TypeError):
                            labor_cost = 0
                        
                        ProposalElementValue.objects.create(
                            proposal=proposal,
                            element=proposal_element,
                            calculated_material_cost=material_cost,
                            calculated_labor_cost=labor_cost,
                            markup_percentage=element.markup_percentage
                        )
                        added_elements.append(element.name)
                        
                except Exception as e:
                    print(f"Error processing element {element.name}: {str(e)}")
                    continue
    
    return {
        "success": True,
        "added_variables": added_variables,
        "updated_variables": updated_variables,
        "added_elements": added_elements
    }

# === Add these endpoints to your api.py file ===

# Endpoint for categories directly related to a proposal
@api.get("/proposals/{proposal_id}/categories", response=List[CategorySchema])
def list_proposal_categories(request, proposal_id: int):
    """List all categories for a specific proposal through element values"""
    proposal = get_object_or_404(Proposal, id=proposal_id)
    
    # Get all element values for this proposal
    element_values = ProposalElementValue.objects.filter(proposal=proposal).select_related('element')
    
    # Get all unique categories from these elements
    category_ids = set()
    categories = []
    
    for element_value in element_values:
        # Skip elements without categories
        if not element_value.element.category:
            continue
            
        category = element_value.element.category
        if category.id not in category_ids:
            category_ids.add(category.id)
            categories.append(category)
    
    return categories

# Endpoint for creating a category directly for a proposal
@api.post("/proposals/{proposal_id}/categories", response=CategorySchema)
def create_proposal_category(request, proposal_id: int, data: CategoryCreateSchema):
    """Create a new category for a specific proposal"""
    proposal = get_object_or_404(Proposal, id=proposal_id)
    
    # Create a new category directly linked to the proposal
    category = ProposalCategory.objects.create(
        proposal=proposal,
        template=None,
        **data.dict()
    )
    
    return category

# Endpoint for creating an element directly for a proposal
@api.post("/proposals/{proposal_id}/elements", response=ElementSchema)
def create_proposal_element(request, proposal_id: int, data: dict):
    """Create a new element for a specific proposal"""
    proposal = get_object_or_404(Proposal, id=proposal_id)
    
    # Extract data
    element_name = data.get("element_name")
    category_name = data.get("category_name")
    material_cost = data.get("material_cost", "0")
    labor_cost = data.get("labor_cost", "0")
    markup_percentage = data.get("markup_percentage", 0)
    position = data.get("position", 0)
    
    # Find or create the category if specified
    category = None
    if category_name:
        try:
            # Try to find an existing category
            category = ProposalCategory.objects.get(
                name=category_name,
                proposal=proposal
            )
        except ProposalCategory.DoesNotExist:
            # Create a new category
            category = ProposalCategory.objects.create(
                name=category_name,
                proposal=proposal,
                template=None,
                position=0
            )
    
    # Create the element
    element = ProposalElement.objects.create(
        name=element_name,
        category=category,
        material_cost=material_cost,
        labor_cost=labor_cost,
        markup_percentage=markup_percentage,
        position=position,
        proposal=proposal
    )
    
    # Also create an initial element value
    ProposalElementValue.objects.create(
        proposal=proposal,
        element=element,
        calculated_material_cost=0,
        calculated_labor_cost=0,
        markup_percentage=markup_percentage
    )
    
    return element

# Import additional required modules
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from pathlib import Path

# Add new schema for file uploads
class FileUploadSchema(Schema):
    initials: str

# Add endpoint for client signature upload
@api.post("/contracts/{contract_id}/upload-client-signature", response=ContractSchema)
def upload_client_signature(request, contract_id: int, initials: str = Form(...), signature_file: UploadedFile = File(...)):
    """Upload a signature image for a client and sign the contract"""
    contract = get_object_or_404(Contract, id=contract_id)
    
    # Save the uploaded file
    file_path = f"signatures/client_{contract_id}_{Path(signature_file.name).name}"
    saved_path = default_storage.save(file_path, ContentFile(signature_file.read()))
    
    # Update the contract - store just the relative path without media/ prefix
    contract.client_signature = saved_path
    contract.client_initials = initials
    contract.client_signed_at = datetime.now()
    contract.save()
    
    print(f"DEBUG - Saved client signature to path: {saved_path}")
    return contract

# Add endpoint for contractor signature upload
@api.post("/contracts/{contract_id}/upload-contractor-signature", response=ContractSchema)
def upload_contractor_signature(request, contract_id: int, initials: str = Form(...), signature_file: UploadedFile = File(...)):
    """Upload a signature image for a contractor and sign the contract"""
    contract = get_object_or_404(Contract, id=contract_id)
    
    # Save the uploaded file
    file_path = f"signatures/contractor_{contract_id}_{Path(signature_file.name).name}"
    saved_path = default_storage.save(file_path, ContentFile(signature_file.read()))
    
    # Update the contract - store just the relative path without media/ prefix
    contract.contractor_signature = saved_path
    contract.contractor_initials = initials
    contract.contractor_signed_at = datetime.now()
    contract.save()
    
    print(f"DEBUG - Saved contractor signature to path: {saved_path}")
    return contract

# Add this endpoint to the Contract APIs section

@api.delete("/contracts/{contract_id}")
def delete_contract(request, contract_id: int):
    contract = get_object_or_404(Contract, id=contract_id)
    
    # Optional: Check if the contract is signed and maybe prevent deletion
    # if contract.client_signed_at or contract.contractor_signed_at:
    #     return api.create_response(request, {"detail": "Cannot delete a signed contract"}, status=400)
    
    # If there are signature files, delete them as well
    if contract.client_signature:
        try:
            default_storage.delete(contract.client_signature)
        except Exception as e:
            print(f"Error deleting client signature: {e}")
    
    if contract.contractor_signature:
        try:
            default_storage.delete(contract.contractor_signature)
        except Exception as e:
            print(f"Error deleting contractor signature: {e}")
    
    # Delete the contract
    contract.delete()
    
    return {"success": True}