const AWS = require('aws-sdk');

const dynamodb = new AWS.DynamoDB.DocumentClient();

exports.handler = async (event, context) => {
    const body = event.body;
    const userId = event.userId;

    // Update DynamoDB table with data from event
    const params = {
        TableName: 'sample-table',
        Key: { id: userId },
        UpdateExpression: 'SET #data = :data',
        ExpressionAttributeNames: { '#data': 'data' },
        ExpressionAttributeValues: { ':data': body }
    };

    await dynamodb.update(params).promise();

    const response = {
        statusCode: 200,
        body: JSON.stringify({ message: 'Success', userId: userId })
    };

    return response;
};
