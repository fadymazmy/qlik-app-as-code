# The Custom UI stays inside the Qlik app

The App must look unlike an out-of-the-box Qlik app, and the usual route to a fully custom look is a separate web page that embeds Qlik charts (a mashup). We decided against that: the Custom UI is produced only by a custom theme, native objects and Custom Extensions, so the App is opened from the Qlik Cloud hub like any other. The point of the project is to show the team what Qlik development itself can reach when it is done as code, and a separate web page would prove web development skill instead and add hosting, authentication and a second codebase to maintain.

## Consequences

- The design is limited to what theme JSON and Custom Extensions can express. Qlik removed CSS overrides of object cards from Cloud themes in August 2026, and CSS that targets Qlik's page structure is unsupported, so neither is used.
- Some of Qlik's own chrome may remain visible and cannot be restyled. Where the approved mock-up cannot be reproduced, the closest result achievable inside Qlik is preferred over leaving Qlik.
