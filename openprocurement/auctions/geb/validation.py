# -*- coding: utf-8 -*-
from datetime import timedelta
from schematics.exceptions import ValidationError
from schematics.types import BaseType
from openprocurement.auctions.core.validation import (
    validate_data
)

from openprocurement.auctions.core.utils import (
    get_now,
    calculate_business_date
)
from openprocurement.auctions.geb.constants import (
    AUCTION_DOCUMENT_STATUSES,
    AUCTION_STATUS_FOR_ADDING_QUESTIONS,
    AUCTION_STATUS_FOR_CHANGING_QUESTIONS,
    AUCTION_STATUS_FOR_CHANGING_ITEMS,
    AUCTION_STATUS_FOR_DELETING_BIDS,
    BID_STATUSES_FOR_ADDING_DOCUMENTS,
    CAV_PS_CODES,
    EDIT_AUCTION_DOCUMENT_STATUSES,
    MIN_NUMBER_OF_DAYS_TENDERING,
    PROCEDURE_DOCUMENT_STATUSES,
    RECTIFICATION_PERIOD_DURATION
)


def validate_change_bid_check_auction_status(request, **kwargs):
    if request.authenticated_role == 'Administrator':
        return True
    if request.validated['auction_status'] not in ['active.tendering', 'active.enquiry']:
        err_msg = 'Can\'t update bid in current ({}) auction status'.format(request.validated['auction_status'])
        request.errors.add('body', 'data', err_msg)
        request.errors.status = 403
        return False
    return True


def validate_change_bid_check_status(request, **kwargs):
    bid = kwargs['bid']

    status = bid.status
    auction_status = request.validated['auction_status']
    new_status = request.validated['json_data'].get('status')

    if request.authenticated_role == 'Administrator':
        return True

    try:
        if new_status != 'pending' and status == 'draft':
            raise Exception('Can\'t update bid status, only from draft you can switch to pending')

        if new_status == 'pending' and auction_status != 'active.tendering':
            raise Exception('Can`t activate bid, can only in active.tendering Auction status')

    except Exception as err:
        request.errors.add('body', 'data', err.message)
        request.errors.status = 403
        return False
    return True


def validate_make_active_status_bid(request, **kwargs):
    bid = kwargs['bid']
    auction = kwargs['auction']

    now = get_now()
    bid_documents = bid.documents
    new_data = request.validated['json_data']

    if request.authenticated_role == 'Administrator' or new_data.get('status') != 'active':
        return True

    try:
        if auction.enquiryPeriod.startDate > now or now > auction.enquiryPeriod.endDate:
            raise Exception('Can`t activate bid, can only in enquiry Period Auction status')

        if not any([document.documentType == 'eligibilityDocuments' for document in bid_documents]):
            raise Exception('Can`t activate bid, need document of documentType: eligibilityDocuments')

        if bid.qualified is not True and not new_data.get('qualified'):
            raise Exception('Can`t activate bid, qualified must be True')

        if not bid.bidNumber and not new_data.get('bidNumber'):
            raise Exception('Can`t activate bid, you must add the bidNumber')

    except Exception as err:
        request.errors.add('body', 'data', err.message)
        request.errors.status = 403
        return False
    return True


def validate_patch_auction_data(request, **kwargs):
    validate_data(request, request.auction.__class__)


def check_auction_status_for_deleting_bids(request):
    auction = request.context.__parent__
    status = auction['status']

    if status not in AUCTION_STATUS_FOR_DELETING_BIDS:
        err_msg = 'Can\'t delete bid in current ({}) auction status'.format(status)
        request.errors.add('body', 'data', err_msg)
        request.errors.status = 403
        return False
    return True


def validate_document_adding_period(request):
    status = request.context.status
    role = request.authenticated_role

    if role != 'auction':
        auction_not_in_editable_state = status not in PROCEDURE_DOCUMENT_STATUSES
    else:
        auction_not_in_editable_state = status not in AUCTION_DOCUMENT_STATUSES

    if auction_not_in_editable_state:
        err_msg = 'Can\'t make document operations in current ({}) auction status'.format(status)
        request.errors.add('body', 'data', err_msg)
        request.errors.status = 403
        return False
    return True


def validate_question_adding_period(request):
    auction = request.context

    if auction.status not in AUCTION_STATUS_FOR_ADDING_QUESTIONS:
        err_msg = 'Can add question only in {}'.format(AUCTION_STATUS_FOR_ADDING_QUESTIONS)
        request.errors.add('body', 'data', err_msg)
        request.errors.status = 403
        return False
    return True


def validate_question_changing_period(request, **kwargs):
    auction = kwargs['auction']

    if auction.status not in AUCTION_STATUS_FOR_CHANGING_QUESTIONS:
        err_msg = 'Can update question only in {}'.format(AUCTION_STATUS_FOR_CHANGING_QUESTIONS)
        request.errors.add('body', 'data', err_msg)
        request.errors.status = 403
        return False
    return True


def cav_ps_code_validator(data, code):
    if code not in CAV_PS_CODES:
        raise ValidationError(BaseType.MESSAGES['choices'].format(CAV_PS_CODES))


def validate_first_auction_status(request):
    status = request.json_body['data'].get('status')
    if status and status != 'draft':
        err_msg = "Auction status must be draft"
        request.errors.add('body', 'data', err_msg)
        request.errors.status = 403
        return False
    return True


def validate_bid_document(request):
    auction = request.context.__parent__

    if auction.status not in BID_STATUSES_FOR_ADDING_DOCUMENTS:
        err_msg = 'Can\'t document in current ({}) auction status'.format(auction.status)
        request.errors.add('body', 'data', err_msg)
        request.errors.status = 403
        return
    return True


def validate_phase_commit(request, **kwargs):
    auction = kwargs['auction']
    new_status = request.validated['json_data'].get('status')
    status = auction.status

    if new_status != 'active.rectification' and status == 'draft':
        err_msg = 'Can\'t switch to ({}) only to active.rectification'.format(new_status)
        request.errors.add('body', 'data', err_msg)
        request.errors.status = 403
        return False
    return True


def validate_bid_initialization(request):
    new_status = request.validated['json_data'].get('status')
    if new_status != 'pending':
        return False
    return True


def validate_auctionPeriod(request):
    auction = request.validated['json_data']
    if not auction.get('auctionPeriod') or not auction['auctionPeriod'].get('startDate'):
        err_msg = 'You must set auctionPeriod start date'
        request.errors.add('body', 'data', err_msg)
        request.errors.status = 422
        return False
    return True


def validate_auction_auction_status(request):
    auction = request.context

    if auction.status != 'active.auction':
        msg = 'Not valid auction status'
        request.errors.add('body', 'data', msg)
        request.errors.status = 403
        return False
    return True


def validate_auction_number_of_bids(request):
    auction = request.context
    bids = request.validated['data'].get('bids', [])

    if len(bids) != len(auction.bids):
        err_msg = "Number of auction results did not match the number of auction bids"
        request.errors.add('body', 'bids', err_msg)
        request.errors.status = 422
        return False
    return True


def validate_auction_identity_of_bids(request):
    auction = request.context
    bids = request.validated['data'].get('bids', [])

    if set([bid['id'] for bid in bids]) != set([bid.id for bid in auction.bids]):
        request.errors.add('body', 'bids', "Auction bids should be identical to the auction bids")
        request.errors.status = 422
        return False
    return True


def validate_auctionPeriod_startDate(request):
    auction = request.context

    value = auction.auctionPeriod.startDate
    if not value:
        return
    now = get_now()
    end_rectificationPeriod = calculate_business_date(now, RECTIFICATION_PERIOD_DURATION, auction)
    end_tenderPeriod = calculate_business_date(end_rectificationPeriod, MIN_NUMBER_OF_DAYS_TENDERING, auction, working_days=True)
    end_enquiry = calculate_business_date(end_tenderPeriod, timedelta(days=3), auction, working_days=True)
    if end_enquiry > value:
        err_msg = "Not enough days for the procedure, change auctionPeriod startDate"
        request.errors.add('body', 'data', err_msg)
        request.errors.status = 422
        return False
    return True


def validate_edit_auction_document_period(request, **kwargs):
    """
    Validate period in which can edit auction document
    """
    auction = kwargs['auction']

    if auction.status not in EDIT_AUCTION_DOCUMENT_STATUSES:
        return False
    return True


def validate_item_changing_period(request, **kwargs):
    """
    Validate period in which can edit auction item
    """
    auction = kwargs['auction']

    if auction.status not in AUCTION_STATUS_FOR_CHANGING_ITEMS:
        err_msg = 'Can update question only in {}'.format(AUCTION_STATUS_FOR_CHANGING_ITEMS)
        request.errors.add('body', 'data', err_msg)
        request.errors.status = 403
        return False
    return True