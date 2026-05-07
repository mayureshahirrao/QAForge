"""
features/steps/grpc_steps.py — gRPC step definitions.

These steps assume protoc-generated stubs at
`src/qaforge/api/grpc/generated/user_service_pb2{,_grpc}.py`. Generate with:
    python -m grpc_tools.protoc -I proto \
        --python_out=src/qaforge/api/grpc/generated \
        --grpc_python_out=src/qaforge/api/grpc/generated proto/user_service.proto
"""
from behave import given, then, when


def _import_stubs():
    from qaforge.api.grpc.generated import user_service_pb2 as pb
    from qaforge.api.grpc.generated import user_service_pb2_grpc as pb_grpc
    return pb, pb_grpc


@given('I authenticate the gRPC client with role "{role}"')
def step_grpc_auth(context, role):
    context.grpc.with_oauth(scope="read write" if role != "viewer" else "read")
    pb, pb_grpc = _import_stubs()
    context.grpc_pb = pb
    context.grpc_stub = context.grpc.stub(pb_grpc.UserServiceStub)


@when('I call GetUser with id "{user_id}"')
def step_grpc_get_user(context, user_id):
    req = context.grpc_pb.GetUserRequest(id=user_id)
    context.grpc_resp = context.grpc_stub.GetUser(req, metadata=context.grpc.auth_metadata())


@when('I call ListUsers (server streaming) with page {page:d} and limit {limit:d}')
def step_grpc_list(context, page, limit):
    req = context.grpc_pb.ListUsersRequest(page=page, limit=limit)
    call = context.grpc_stub.ListUsers(req, metadata=context.grpc.auth_metadata())
    context.grpc_stream = context.grpc.collect_server_stream(call)


@then('the gRPC user response email should equal "{email}"')
def step_grpc_email(context, email):
    assert context.grpc_resp.email == email, f"Got {context.grpc_resp.email}"


@then('the gRPC server stream should contain at least {n:d} users')
def step_grpc_stream_count(context, n):
    assert len(context.grpc_stream) >= n, f"Got {len(context.grpc_stream)}"
