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
        Then I am taken to the edit page for that entry

    Scenario: Markdown Entries
        Given a journal edit form
        When I type in the edit box
        Then I can use Markdown to format my post

    Scenario: Code blocks
        Given a journal detail page
        When I look at a post
        Then I can see colorized code samples