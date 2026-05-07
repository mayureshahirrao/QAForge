"""
qaforge.api.graphql.operations
==============================
Pre-defined GraphQL queries and mutations used in tests.
Keep operations here — never inline them in step files.
"""

GET_USER_QUERY = """
query GetUser($id: ID!) {
  user(id: $id) {
    id
    email
    fullName
    role
    createdAt
  }
}
"""

LIST_USERS_QUERY = """
query ListUsers($page: Int!, $limit: Int!) {
  users(page: $page, limit: $limit) {
    items { id email fullName role }
    total
    page
    limit
  }
}
"""

CREATE_USER_MUTATION = """
mutation CreateUser($input: CreateUserInput!) {
  createUser(input: $input) {
    id
    email
    fullName
  }
}
"""

DELETE_USER_MUTATION = """
mutation DeleteUser($id: ID!) {
  deleteUser(id: $id) { success }
}
"""
