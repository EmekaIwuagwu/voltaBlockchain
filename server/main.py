import sys
import os

# Add the root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from concurrent import futures
import grpc
from proto import blockchain_pb2_grpc as pb2_grpc
from proto import blockchain_pb2 as pb2
import blockchain as blockchain_lib
from db import database

# Ensure database tables are created
database.create_tables()

# Initialize blockchain
blockchain_lib.initialize_blockchain()

class BlockchainService(pb2_grpc.BlockchainServiceServicer):

    def CreateAddress(self, request, context):
        result = blockchain_lib.create_address()
        response = pb2.UserAddress(
            address=result["address"],
            balance=result["balance"],
            uuid=result["uuid"],
            passkey=result["passkey"]
        )
        return response

    def SendTokens(self, request, context):
        result = blockchain_lib.create_transaction(
            request.addressFrom,
            request.addressTo,
            request.amount,
            request.passkey
        )
        if "error" in result:
            context.set_details(result["error"])
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return pb2.TransactionResponse()
        else:
            response = pb2.TransactionResponse(
                from_address=request.addressFrom,
                to_address=request.addressTo,
                amount=request.amount,
                txHash=result["txHash"]
            )
            return response

    def CheckBalance(self, request, context):
        result = blockchain_lib.check_balance(request.address)
        if "error" in result:
            context.set_details(result["error"])
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return pb2.BalanceResponse()
        else:
            response = pb2.BalanceResponse(
                address=request.address,
                balance=result["balance"]
            )
            return response

    def CheckTransactions(self, request, context):
        result = blockchain_lib.check_transactions(request.address)
        if "error" in result:
            context.set_details(result["error"])
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return pb2.TransactionHistoryResponse()
        else:
            transactions = [
                pb2.Transaction(
                    from_address=tx["from"],
                    to_address=tx["to"],
                    amount=tx["amount"],
                    date=tx["date"]
                ) for tx in result["transactions"]
            ]
            response = pb2.TransactionHistoryResponse(
                transactions=transactions
            )
            return response

    def RequestLoan(self, request, context):
        result = blockchain_lib.request_loan(
            request.address,
            request.amount,
            request.reason
        )
        if "error" in result:
            context.set_details(result["error"])
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return pb2.LoanResponse()
        else:
            response = pb2.LoanResponse(
                message=result["message"],
                previous_balance=result["previous_balance"],
                updated_balance=0.0  # Assuming updated_balance should be 0 as loans do not change balance immediately
            )
            return response

    def PayBackLoan(self, request, context):
        result = blockchain_lib.pay_back_loan(
            request.address,
            request.amount
        )
        if "error" in result:
            context.set_details(result["error"])
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return pb2.LoanResponse()
        else:
            response = pb2.LoanResponse(
                message=result["message"],
                previous_balance=result["previous_balance"],
                updated_balance=0.0  # Assuming updated_balance should be 0 as paying back does not change balance immediately
            )
            return response

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_BlockchainServiceServicer_to_server(BlockchainService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server started. Listening on port 50051.")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
