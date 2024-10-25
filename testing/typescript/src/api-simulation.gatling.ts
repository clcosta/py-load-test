import { atOnceUsers, scenario, simulation, pause, jsonPath, exec, StringBody, bodyBytes, rampUsers } from "@gatling.io/core";
import { http, HttpRequestActionBuilder, status } from "@gatling.io/http";

namespace ApiTypes {
  export type Auth = {
    access_token: string;
  };
  export type DataResponse = {
    id: string;
    data: number[] | { users: number[]; posts: number[] };
  };
  export type User = {
    id: string;
  };
  export enum Kind {
    Users = "users",
    Posts = "posts"
  }
}

const getOperation = (kind: ApiTypes.Kind) => {
  return http(`Get ${kind} kind data`)
    .get(`/data/${kind}`)
    .header("Authorization", (session) => session.get("accessToken"))
    .check(status().is(200))
    .check(jsonPath("$.id").is((session) => session.get("userId")))
    .check(jsonPath("$.data").notNull())
    .check(jsonPath("$.data").ofList().notNull());
}

const createOperation = (kind: ApiTypes.Kind, value: number) => {
  return http(`Create ${kind}`)
    .post(`/data/${kind}`)
    .header("Authorization", (session) => session.get("accessToken"))
    .queryParam("value", value)
    .check(status().is(201))
    .check(jsonPath("$.id").is((session) => session.get("userId")))
    .check(jsonPath("$.data").notNull())
    .check(jsonPath("$.data").ofList().notNull());
}

const updateOperation = (kind: ApiTypes.Kind, value: number, newValue: number) => {
  return http(`Update ${kind}`)
    .put(`/data/${kind}`)
    .header("Authorization", (session) => session.get("accessToken"))
    .body(StringBody(JSON.stringify({ old: value, new: newValue })))
    .check(status().is(200))
    .check(jsonPath("$.id").is((session) => session.get("userId")))
    .check(jsonPath("$.data").notNull())
    .check(jsonPath("$.data").ofList().notNull());
}


const deleteOperation = (kind: ApiTypes.Kind, value: number) => {
  return http(`Delete ${kind}`)
    .delete(`/data/${kind}`)
    .header("Authorization", (session) => session.get("accessToken"))
    .queryParam("value", value)
    .check(status().is(200))
    .check(jsonPath("$.id").is((session) => session.get("userId")))
    .check(jsonPath("$.data").notNull())
    .check(jsonPath("$.data").ofList().notNull());
}

const crudOperations = (kind: ApiTypes.Kind) => {
  const value = Math.floor(Math.random() * 100);
  const newValue = Math.floor(Math.random() * 100);
  return exec(getOperation(kind))
    .pause(1)
    .exec(createOperation(kind, value))
    .pause(1)
    .exec(updateOperation(kind, value, newValue))
    .pause(1)
    .exec(deleteOperation(kind, newValue))
}

export default simulation((setUp) => {
  // http
  const httpProtocol = http
    .baseUrl("http://localhost:8000")
    .acceptHeader("application/json")
    .contentTypeHeader("application/json");

  // scenario
  const baseScenario = scenario("Running once per all routes").exec(
    http("Get Access Token")
      .post("/auth")
      .check(status().is(200))
      .check(jsonPath("$.access_token").saveAs("accessToken")),
    pause(1),
    http("Get me unauthorized").get("/me").check(status().is(403)),
    pause(1),
    http("Get me")
      .get("/me")
      .header("Authorization", (session) => session.get("accessToken"))
      .check(status().is(200))
      .check(jsonPath("$.id_user").saveAs("userId")),
    pause(1),
    // GET
    http("Get all data")
      .get("/data")
      .header("Authorization", (session) => session.get("accessToken"))
      .check(status().is(200))
      .check(jsonPath("$.id").is((session) => session.get("userId")))
      .check(jsonPath("$.data").notNull())
      .check(jsonPath("$.data.users").ofObject().notNull()),
    pause(1),

    // USERS
    crudOperations(ApiTypes.Kind.Users),
    // POSTS
    crudOperations(ApiTypes.Kind.Posts),
    // Sample File download
    http("Download file")
      .get("/sample")
      .check(status().is(200))
      .check(bodyBytes().saveAs("file"))
      .check(bodyBytes().transform((bytes) => bytes.length > 0).is(true))
  );

  // 1-1500 users
  setUp(baseScenario.injectOpen(
    atOnceUsers(1),
    rampUsers(1500).during(15)
  ).protocols(httpProtocol))
});
