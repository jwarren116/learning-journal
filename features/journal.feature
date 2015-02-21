Feature: Journal Editing
    Implement the ability to edit posts in a rich manner

    Scenario: Entry Detail
        Given a journal home page
        When I click on the entry link
        Then I get the detail page for that entry

    Scenario: Post Edit
        Given a logged in user
        And a journal detail page
        When I click on the edit button
        Then the edit form displays

    Scenario: Markdown Entries
        Given a journal edit form
        When I edit a post
        Then I can use Markdown to format my post

    Scenario: Code blocks
        Given a journal detail page
        When I look at a post
        Then I can see colorized code samples

    Scenario: AJAX
        Given a journal detail page
        When I edit a post
        Then the page does not reload

    Scenario: Tweet Button
        Given a detail page with a Twitter button
        When I click the Tweet button
        Then my post is Tweeted
